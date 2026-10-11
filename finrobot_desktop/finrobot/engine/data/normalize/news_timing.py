"""Event-time observability gate + contamination attribution — pure, zero-I/O.

Item 3 of ``strategies/qfin-tr/llm-trading-systems.md`` §5 (the "event-time
observability gate and contamination attribution" buildable now): decide *when* a
news-derived signal may first be acted on, and *whether* the article it came from
could already have been memorised by the model that produced it. Two orthogonal
responsibilities, one per §4 pitfall:

* :func:`classify_publication` — the US-equity publication rule. A pre-open
  article (strictly before 09:30 ET) is observable before the opening bell, so it
  may trade the SAME session; anything at/after the open — including an
  after-close, weekend or holiday release — can only enter on the NEXT session,
  because acting earlier would use a price that had not formed when the text was
  observable (the §4 "pre-observation price movement" leak). The phase label
  REUSES ``session.SessionState`` and ``session``'s exchange resolution; this
  module never grows a second session taxonomy.
* :func:`observability_gate` — the contamination gate. A foundation model may
  have memorised any article published at or before its disclosed
  data-freshness cutoff, so those observations must not enter a reported metric.
  §2.7 / §5 pass-criterion: the raw (pre-cutoff) Sharpe is materially *above* the
  post-cutoff one — :func:`contamination_sharpe_contrast` is the pure helper that
  makes that comparison assertable from two labelled return series.

Everything here is deterministic and I/O-free. The only calendar knowledge is the
pure NYSE holiday set below — no third-party calendar library and no network,
because "the next session" is not derivable from a weekday check alone (a release
on a market holiday must defer past it). Not modelled, and deliberately so: ad-hoc
closures (national days of mourning), half-day early closes (13:00 ET) — the
`session` label can over-report `live`/`post_market` in the 13:00–16:00 window of
a half-day, but the *eligible* session is unaffected because that window is still
at/after the open.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from finrobot.engine.backtest.validation.stats import annualized_sharpe
from finrobot.engine.data.normalize.session import (
    SessionState,
    _coerce_quote_dt,
    _resolve_market_session,
    _US_SESSION,
)

__all__ = [
    "NewsObservation",
    "PublicationTiming",
    "SharpeContrast",
    "classify_publication",
    "contamination_sharpe_contrast",
    "is_us_trading_day",
    "next_us_trading_day",
    "observability_gate",
    "us_market_holidays",
]

#: All publication rules here are US-equity rules, so the ET date is the one the
#: contamination comparison must use: a 2023-12-31 20:00 ET release is
#: 2024-01-01 UTC, and comparing the UTC date would wrongly clear it against a
#: 2023-12-31 cutoff. Taken from ``session``'s US session rather than a second
#: ``ZoneInfo("America/New_York")`` so the two modules cannot drift.
_ET: ZoneInfo = _US_SESSION.tz

# yfinance's extended-session windows (PRE 04:00–09:30 ET, POST 16:00–20:00 ET).
# ``session`` models only the regular window, so these two boundaries are the one
# piece of session-window knowledge carried locally — needed only to label the
# phase honestly (overnight vs pre-market vs after-hours); eligibility depends
# solely on "before the open" vs "at/after the open".
_EXTENDED_PRE_OPEN = time(4, 0)
_EXTENDED_POST_CLOSE = time(20, 0)


def _first_weekday(year: int, month: int, weekday: int) -> date:
    """First ``weekday`` (Mon=0) of ``month``."""
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """``n``-th (1-based) ``weekday`` of ``month``."""
    return _first_weekday(year, month, weekday) + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Last ``weekday`` of ``month``."""
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (the anonymous computus), for Good Friday.

    Good Friday is the only NYSE holiday with no fixed date or week rule, and it
    is *always* closed — so it cannot be skipped without mis-dating the one
    Friday a year when a publication must defer three days.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def _observed_fixed(year: int, month: int, day: int, *, saturday_rolls_back: bool) -> date | None:
    """The observed NYSE date for a fixed-date holiday, or ``None`` if unobserved.

    Sunday rolls forward to Monday; Saturday normally rolls back to the preceding
    Friday, EXCEPT New Year's Day, which the NYSE does not observe on a Saturday
    (Rule 7.2 keeps the last trading day of the year open — e.g. Fri 2021-12-31
    traded although 2022-01-01 was a Saturday).
    """
    d = date(year, month, day)
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1) if saturday_rolls_back else None
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def us_market_holidays(year: int) -> frozenset[date]:
    """Full-day NYSE closures for ``year`` — computed, never table-driven.

    Coverage gaps accepted (they need a maintenance-fed table, not a rule):
    ad-hoc closures (national days of mourning) and half-day early closes.
    Juneteenth is observed only from 2022 (the first year the NYSE closed for it);
    MLK Day from its 1998 federal/NYSE adoption — earlier years are out of scope
    for a news backtest that must anyway start post-cutoff.
    """
    holidays: set[date] = {
        _nth_weekday(year, 1, 0, 3),  # MLK Day — 3rd Monday of January
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday — 3rd Monday of February
        _easter_sunday(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day — last Monday of May
        _nth_weekday(year, 9, 0, 1),  # Labor Day — 1st Monday of September
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving — 4th Thursday of November
    }
    fixed: tuple[date | None, ...] = (
        _observed_fixed(year, 1, 1, saturday_rolls_back=False),  # New Year's Day
        _observed_fixed(year, 7, 4, saturday_rolls_back=True),  # Independence Day
        _observed_fixed(year, 12, 25, saturday_rolls_back=True),  # Christmas
        _observed_fixed(year, 6, 19, saturday_rolls_back=True) if year >= 2022 else None,
    )
    holidays.update(d for d in fixed if d is not None)
    return frozenset(holidays)


def is_us_trading_day(d: date) -> bool:
    """Is ``d`` a full NYSE trading day (weekday, not a full-day holiday)."""
    return d.weekday() < 5 and d not in us_market_holidays(d.year)


def next_us_trading_day(d: date) -> date:
    """The first NYSE trading day strictly after ``d``."""
    nxt = d + timedelta(days=1)
    while not is_us_trading_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def _phase(local_time: time, *, open_: time, close: time) -> SessionState:
    """Phase label on a trading day, in the exchange's local clock.

    Only ``closed`` / ``pre_market`` / ``live`` / ``post_market`` are reachable
    here; ``halted`` needs a per-name provider signal and ``unknown`` means the
    exchange itself was unresolvable (both per ``session``'s contract).
    """
    if local_time < _EXTENDED_PRE_OPEN:
        return "closed"  # overnight — no venue is trading
    if local_time < open_:
        return "pre_market"
    if local_time < close:
        return "live"
    if local_time < _EXTENDED_POST_CLOSE:
        return "post_market"
    return "closed"  # after the after-hours session


class PublicationTiming(BaseModel):
    """When the news was observable, and the first session it may be acted on."""

    model_config = ConfigDict(frozen=True)

    session: SessionState = Field(
        description="Market phase at publication, in session.py's taxonomy"
    )
    eligible_session: AwareDatetime = Field(
        description=(
            "Opening bell (09:30 ET) of the first session on which a signal "
            "derived from this publication may be acted on"
        )
    )


def classify_publication(
    ts: datetime | str | int | float, *, exchange: str | None = None
) -> PublicationTiming:
    """Classify a news timestamp against the US-equity publication rules.

    ``ts`` accepts the shapes providers actually emit (eodhd news is unix epoch
    seconds; ISO strings and datetimes also arrive) via ``session``'s coercion
    helper, so the caller does not re-implement timestamp parsing.

    ``exchange`` is the ticker's provider exchange string, resolved through
    ``session``'s exchange mapping: only a US-resolvable (or absent) exchange gets
    a US rule applied. A clearly foreign/unrecognized exchange yields
    ``session="unknown"`` with ``eligible_session`` at the publication instant —
    the gate refuses to invent a US eligibility for a listing whose session it
    cannot prove. Raises ``ValueError`` on an unparseable ``ts``.
    """
    coerced = _coerce_quote_dt(ts)
    if coerced is None:
        raise ValueError(f"unparseable news timestamp: {ts!r}")
    session = _resolve_market_session(None, exchange)
    if session is None:
        return PublicationTiming(session="unknown", eligible_session=coerced.astimezone(_ET))
    local = coerced.astimezone(session.tz)
    today = local.date()
    before_open = local.time() < session.open
    if is_us_trading_day(today):
        phase = _phase(local.time(), open_=session.open, close=session.close)
        eligible_date = today if before_open else next_us_trading_day(today)
    else:
        # Weekend / holiday: no session today, whatever the clock says.
        phase = "closed"
        eligible_date = next_us_trading_day(today)
    return PublicationTiming(
        session=phase,
        eligible_session=datetime.combine(eligible_date, session.open, tzinfo=session.tz),
    )


def _et_date(dt: datetime) -> date:
    """The ET calendar date of ``dt`` — the cutoffs are US data-freshness dates."""
    return dt.astimezone(_ET).date()


class NewsObservation(BaseModel):
    """One news article plus the provenance needed to judge contamination.

    ``model_release_date`` is carried but not scored: it is the audit trail
    behind the cutoff (the §2.7 release-date buffer is a *test-window* decision),
    while ``pretraining_cutoff`` is the date that decides membership.
    """

    model_config = ConfigDict(frozen=True)

    published_at: AwareDatetime
    timing: PublicationTiming
    model_id: str
    model_release_date: date | None = None
    pretraining_cutoff: date | None = None

    @property
    def contaminated(self) -> bool:
        """Did the model's pretraining window plausibly cover this publication?

        True when the publication date is at or before the declared cutoff. The
        boundary is deliberately inclusive: a same-day article is indistinguishable
        from the tail of the pretraining corpus, and the cost of wrongly keeping it
        (a memorisation-inflated metric) exceeds the cost of dropping it. With no
        declared cutoff nothing can be proven, so it reports False — the gate's
        ``as_of_cutoff`` is the fallback for exactly that case.
        """
        if self.pretraining_cutoff is None:
            return False
        return _et_date(self.published_at) <= self.pretraining_cutoff


def _defer_one_trading_day(obs: NewsObservation) -> NewsObservation:
    """The stricter arm: push the eligible session one trading day later.

    Only ``eligible_session`` moves (the publication phase is a fact about the
    release). Exactly one *trading* day is added — a Friday eligible session lands
    on Monday, and a session before a holiday lands after it — because the arm
    models "the signal is only implementable a day later", not a calendar shift.
    """
    eligible = obs.timing.eligible_session.astimezone(_ET)
    nxt = next_us_trading_day(eligible.date())
    shifted = eligible.replace(year=nxt.year, month=nxt.month, day=nxt.day)
    timing = obs.timing.model_copy(update={"eligible_session": shifted})
    return obs.model_copy(update={"timing": timing})


def observability_gate(
    observations: Iterable[NewsObservation],
    *,
    as_of_cutoff: date,
    delay_one_day: bool = False,
) -> list[NewsObservation]:
    """The usable, post-cutoff subset of ``observations``, in input order.

    Cutoff precedence is per-observation first (an article that declares the model
    it was scored with must be judged against *that* model's cutoff), falling back
    to ``as_of_cutoff`` for articles carrying no declaration.

    ``delay_one_day=True`` selects §4's stricter robustness arm: every signal in
    the surviving subset is deferred a full trading day, so a metric reported both
    ways shows how much of the edge depends on same-session execution.
    """
    usable: list[NewsObservation] = []
    for obs in observations:
        cutoff = obs.pretraining_cutoff
        if cutoff is None:
            cutoff = as_of_cutoff
        if _et_date(obs.published_at) <= cutoff:
            continue
        usable.append(_defer_one_trading_day(obs) if delay_one_day else obs)
    return usable


class SharpeContrast(NamedTuple):
    """The same signal's annualized Sharpe on two cut-off slices (§2.7)."""

    pre_cutoff: float
    post_cutoff: float

    @property
    def overstatement(self) -> float:
        """How much of the headline number the contamination gate removes."""
        return self.pre_cutoff - self.post_cutoff


def contamination_sharpe_contrast(
    pre_cutoff_returns: Sequence[float],
    post_cutoff_returns: Sequence[float],
    *,
    periods_per_year: int = 252,
) -> SharpeContrast:
    """Annualized Sharpe of each labelled slice, in the shared per-period basis.

    Both slices must be annualized on the *same* ``periods_per_year`` or the
    comparison is meaningless; the returns-convention math is
    ``validation.stats``', not a second copy here.
    """
    return SharpeContrast(
        pre_cutoff=annualized_sharpe(pre_cutoff_returns, periods_per_year=periods_per_year),
        post_cutoff=annualized_sharpe(post_cutoff_returns, periods_per_year=periods_per_year),
    )
