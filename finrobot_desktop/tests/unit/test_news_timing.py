"""Unit tests for the event-time observability gate (``normalize.news_timing``).

The three claims the module must earn (§4/§5.3 of
``strategies/qfin-tr/llm-trading-systems.md``), each tested against an externally
knowable boundary rather than the implementation:

1. publication timing — the 09:30 ET boundary, after-close / weekend / holiday
   deferral, and DST (March and November) all resolve to the right *UT instant*;
2. the contamination gate — a pre-cutoff article is dropped, a post-cutoff one
   survives, and the per-article cutoff wins over the report-wide fallback;
3. the stricter arm — every eligible session moves exactly one *trading* day.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from finrobot.engine.backtest.validation.stats import annualized_sharpe
from finrobot.engine.data.normalize.news_timing import (
    NewsObservation,
    classify_publication,
    contamination_sharpe_contrast,
    is_us_trading_day,
    next_us_trading_day,
    observability_gate,
    us_market_holidays,
)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

#: Post-cutoff test start per §2.7 (MFAST starts 1 Jun 2024, after the Apr 2024
#: checkpoint release); the cutoff itself is the Llama-3 70B Dec-2023 freshness.
CUTOFF = date(2023, 12, 31)


def _obs(
    published_at: datetime, *, cutoff: date | None = None, model_id: str = "llama-3-70b"
) -> NewsObservation:
    return NewsObservation(
        published_at=published_at,
        timing=classify_publication(published_at),
        model_id=model_id,
        pretraining_cutoff=cutoff,
    )


def _et(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=ET)


# --------------------------------------------------------------------------- #
# 1. publication timing
# --------------------------------------------------------------------------- #

# (label, timestamp, expected phase, expected eligible session)
BOUNDARY_TABLE = [
    ("friday 16:00 close -> monday", _et(2026, 6, 5, 16, 0), "post_market", _et(2026, 6, 8, 9, 30)),
    (
        "friday after-hours -> monday",
        _et(2026, 6, 5, 17, 30),
        "post_market",
        _et(2026, 6, 8, 9, 30),
    ),
    ("saturday -> monday", _et(2026, 6, 6, 12, 0), "closed", _et(2026, 6, 8, 9, 30)),
    ("sunday -> monday", _et(2026, 6, 7, 12, 0), "closed", _et(2026, 6, 8, 9, 30)),
    (
        "pre-open 09:29:59 -> same session",
        _et(2026, 6, 9, 9, 29, 59),
        "pre_market",
        _et(2026, 6, 9, 9, 30),
    ),
    (
        "at the open 09:30:00 -> next session",
        _et(2026, 6, 9, 9, 30, 0),
        "live",
        _et(2026, 6, 10, 9, 30),
    ),
    (
        "still 09:30:00.5 -> next session",
        _et(2026, 6, 9, 9, 30, 0, 500000),
        "live",
        _et(2026, 6, 10, 9, 30),
    ),
    ("intraday -> next session", _et(2026, 6, 9, 12, 0), "live", _et(2026, 6, 10, 9, 30)),
    ("15:59:59 -> next session", _et(2026, 6, 9, 15, 59, 59), "live", _et(2026, 6, 10, 9, 30)),
    ("16:00 close -> next session", _et(2026, 6, 9, 16, 0), "post_market", _et(2026, 6, 10, 9, 30)),
    ("overnight 02:00 -> same session", _et(2026, 6, 9, 2, 0), "closed", _et(2026, 6, 9, 9, 30)),
    (
        "pre-market 05:00 -> same session",
        _et(2026, 6, 9, 5, 0),
        "pre_market",
        _et(2026, 6, 9, 9, 30),
    ),
    (
        "21:00 after post-market -> next session",
        _et(2026, 6, 9, 21, 0),
        "closed",
        _et(2026, 6, 10, 9, 30),
    ),
    ("july 4th holiday -> july 5th", _et(2024, 7, 4, 10, 0), "closed", _et(2024, 7, 5, 9, 30)),
    (
        "juneteenth observed monday -> tuesday",
        _et(2022, 6, 20, 10, 0),
        "closed",
        _et(2022, 6, 21, 9, 30),
    ),
]


@pytest.mark.parametrize(
    ("ts", "phase", "eligible"),
    [case[1:] for case in BOUNDARY_TABLE],
    ids=[case[0] for case in BOUNDARY_TABLE],
)
def test_publication_boundary_table(ts: datetime, phase: str, eligible: datetime):
    timing = classify_publication(ts)
    assert timing.session == phase
    assert timing.eligible_session == eligible


def test_holiday_pre_open_does_not_grant_a_same_session_entry():
    """08:00 on a holiday is before 09:30 — but there is no session to enter."""
    timing = classify_publication(_et(2024, 7, 4, 8, 0))
    assert timing.session == "closed"
    assert timing.eligible_session == _et(2024, 7, 5, 9, 30)


def test_dst_march_publication_defers_into_edt():
    """Fri 2026-03-06 (EST) defers over the Mar-8 DST change: eligible is EDT."""
    timing = classify_publication(_et(2026, 3, 6, 16, 30))
    assert timing.eligible_session == _et(2026, 3, 9, 9, 30)
    assert timing.eligible_session.utcoffset() == timedelta(hours=-4)
    assert timing.eligible_session.astimezone(UTC) == datetime(2026, 3, 9, 13, 30, tzinfo=UTC)


def test_dst_november_publication_defers_into_est():
    """Fri 2026-10-30 (EDT) defers over the Nov-1 DST change: eligible is EST."""
    timing = classify_publication(_et(2026, 10, 30, 17, 0))
    assert timing.eligible_session == _et(2026, 11, 2, 9, 30)
    assert timing.eligible_session.utcoffset() == timedelta(hours=-5)
    assert timing.eligible_session.astimezone(UTC) == datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def test_dst_transition_sundays_are_not_trading_days():
    assert is_us_trading_day(date(2026, 3, 8)) is False
    assert is_us_trading_day(date(2026, 11, 1)) is False
    assert is_us_trading_day(date(2026, 11, 2)) is True


def test_provider_epoch_seconds_are_accepted():
    """eodhd news arrives as unix seconds (Sat 2026-06-06 09:00 ET) — no re-parse."""
    timing = classify_publication(1780750800)
    assert timing.session == "closed"
    assert timing.eligible_session == _et(2026, 6, 8, 9, 30)


def test_iso_string_is_accepted_and_agrees_with_the_datetime_form():
    assert classify_publication("2026-06-09T16:00:00Z") == classify_publication(
        _et(2026, 6, 9, 12, 0)
    )


def test_naive_timestamp_is_treated_as_utc():
    naive = classify_publication(datetime(2026, 6, 9, 16, 0))  # naive → UTC = 12:00 ET
    assert naive.session == "live"
    assert naive.eligible_session == _et(2026, 6, 10, 9, 30)


def test_unparseable_timestamp_raises():
    with pytest.raises(ValueError):
        classify_publication("not-a-timestamp")


def test_unmapped_exchange_is_unknown_rather_than_falsely_us():
    """A non-US listing must not inherit US eligibility rules."""
    timing = classify_publication(_et(2026, 6, 9, 12, 0), exchange="XETRA")
    assert timing.session == "unknown"
    assert timing.eligible_session == _et(2026, 6, 9, 12, 0)


def test_us_exchange_hint_keeps_us_rules():
    timing = classify_publication(_et(2026, 6, 9, 12, 0), exchange="NasdaqGS")
    assert timing.session == "live"
    assert timing.eligible_session == _et(2026, 6, 10, 9, 30)


# --------------------------------------------------------------------------- #
# holiday calendar
# --------------------------------------------------------------------------- #


def test_holiday_calendar_matches_known_nyse_2024_dates():
    assert us_market_holidays(2024) == frozenset(
        {
            date(2024, 1, 1),  # New Year's Day (Monday)
            date(2024, 1, 15),  # MLK
            date(2024, 2, 19),  # Washington's Birthday
            date(2024, 3, 29),  # Good Friday (Easter = Mar 31)
            date(2024, 5, 27),  # Memorial Day
            date(2024, 6, 19),  # Juneteenth
            date(2024, 7, 4),  # Independence Day
            date(2024, 9, 2),  # Labor Day
            date(2024, 11, 28),  # Thanksgiving
            date(2024, 12, 25),  # Christmas
        }
    )


def test_new_years_day_is_not_rolled_back_off_a_saturday():
    """NYSE keeps the last trading day of the year open (2021-12-31 traded)."""
    assert date(2021, 12, 31) not in us_market_holidays(2021)
    assert is_us_trading_day(date(2021, 12, 31)) is True
    assert is_us_trading_day(date(2022, 1, 3)) is True


def test_juneteenth_only_observed_from_2022():
    assert date(2021, 6, 18) not in us_market_holidays(2021)
    assert is_us_trading_day(date(2021, 6, 18)) is True
    assert date(2027, 6, 18) in us_market_holidays(2027)  # Sat 2027-06-19 → Friday


def test_next_trading_day_skips_holiday_plus_weekend_block():
    assert next_us_trading_day(date(2024, 3, 29)) == date(2024, 4, 1)  # Fri → Mon
    assert next_us_trading_day(date(2026, 7, 2)) == date(2026, 7, 6)  # Jul-3 holiday


# --------------------------------------------------------------------------- #
# 2. contamination gate
# --------------------------------------------------------------------------- #


def test_gate_drops_pre_cutoff_and_keeps_post_cutoff():
    memorised = _obs(_et(2023, 6, 15, 10, 0), cutoff=CUTOFF, model_id="llama-3-70b")
    honest = _obs(_et(2024, 6, 3, 10, 0), cutoff=CUTOFF, model_id="llama-3-70b")
    assert memorised.contaminated is True
    assert honest.contaminated is False
    assert observability_gate([memorised, honest], as_of_cutoff=CUTOFF) == [honest]


def test_gate_uses_as_of_cutoff_when_the_article_declares_none():
    before = _obs(_et(2023, 6, 15, 10, 0))
    after = _obs(_et(2024, 6, 3, 10, 0))
    assert before.contaminated is False  # nothing declared → nothing proven
    assert observability_gate([before, after], as_of_cutoff=CUTOFF) == [after]


def test_gate_prefers_the_declared_cutoff_over_the_report_cutoff():
    """Each article is judged against the model it was actually scored with."""
    older_model = _obs(_et(2020, 1, 2, 10, 0), cutoff=date(2019, 6, 30), model_id="bert-2019")
    newer_model = _obs(_et(2023, 6, 15, 10, 0), cutoff=date(2024, 6, 30), model_id="model-2024")
    assert observability_gate([older_model], as_of_cutoff=CUTOFF) == [older_model]
    assert observability_gate([newer_model], as_of_cutoff=date(2019, 1, 1)) == []


def test_contamination_boundary_is_inclusive():
    on_cutoff = _obs(_et(2023, 12, 31, 10, 0), cutoff=CUTOFF)
    next_day = _obs(_et(2024, 1, 1, 10, 0), cutoff=CUTOFF)
    assert on_cutoff.contaminated is True
    assert next_day.contaminated is False


def test_contamination_uses_the_et_date_not_the_utc_date():
    """2024-01-01T01:00Z is still 2023-12-31 in New York → inside the cutoff."""
    obs = _obs(datetime(2024, 1, 1, 1, 0, tzinfo=UTC), cutoff=CUTOFF)
    assert obs.published_at.date() == date(2024, 1, 1)  # UTC says post-cutoff
    assert obs.contaminated is True  # ET says pre-cutoff — the US rule wins


def test_news_observation_rejects_naive_timestamps():
    with pytest.raises(ValidationError):
        NewsObservation(
            published_at=datetime(2024, 6, 3, 10, 0),  # naive
            timing=classify_publication(_et(2024, 6, 3, 10, 0)),
            model_id="llama-3-70b",
        )


# --------------------------------------------------------------------------- #
# 3. the stricter arm — one full trading day of deferral
# --------------------------------------------------------------------------- #


def test_delay_one_day_shifts_every_eligible_session_by_one_trading_day():
    observations = [
        _obs(_et(2026, 6, 5, 8, 0)),  # pre-open Friday → eligible Fri 06-05
        _obs(_et(2026, 6, 5, 16, 0)),  # Friday close → eligible Mon 06-08
        _obs(_et(2026, 6, 8, 9, 30)),  # at Monday's open → eligible Tue 06-09
    ]
    plain = observability_gate(observations, as_of_cutoff=CUTOFF)
    strict = observability_gate(observations, as_of_cutoff=CUTOFF, delay_one_day=True)

    assert [o.timing.eligible_session for o in plain] == [
        _et(2026, 6, 5, 9, 30),
        _et(2026, 6, 8, 9, 30),
        _et(2026, 6, 9, 9, 30),
    ]
    assert [o.timing.eligible_session for o in strict] == [
        _et(2026, 6, 8, 9, 30),  # Friday → Monday
        _et(2026, 6, 9, 9, 30),  # Monday → Tuesday
        _et(2026, 6, 10, 9, 30),  # Tuesday → Wednesday
    ]
    for before, after in zip(plain, strict, strict=True):
        assert after.timing.session == before.timing.session  # phase is a fact
        assert next_us_trading_day(before.timing.eligible_session.date()) == (
            after.timing.eligible_session.date()
        )
    # frozen models: the inputs are untouched by the strict arm
    assert observations[0].timing.eligible_session == _et(2026, 6, 5, 9, 30)


def test_delay_one_day_lands_after_a_holiday_weekend_block():
    """Eligible Thu 2026-07-02 + 1 trading day = Mon 2026-07-06 (Jul-3 holiday)."""
    obs = _obs(_et(2026, 7, 1, 16, 0))  # after Wed's close → eligible Thu 07-02
    strict = observability_gate([obs], as_of_cutoff=CUTOFF, delay_one_day=True)
    assert strict[0].timing.eligible_session == _et(2026, 7, 6, 9, 30)


# --------------------------------------------------------------------------- #
# 4. the Sharpe contrast that makes §5's pass criterion assertable
# --------------------------------------------------------------------------- #

# Steady "edge" from memorised news vs a noisier, honest post-cutoff signal.
PRE_CUTOFF_RETURNS = [0.011, 0.009, 0.012, 0.008, 0.010]
POST_CUTOFF_RETURNS = [0.020, -0.010, 0.005, -0.015, 0.005]


def test_pre_cutoff_sharpe_is_the_inflated_one():
    contrast = contamination_sharpe_contrast(PRE_CUTOFF_RETURNS, POST_CUTOFF_RETURNS)
    assert contrast.pre_cutoff == annualized_sharpe(PRE_CUTOFF_RETURNS, periods_per_year=252)
    assert contrast.post_cutoff == annualized_sharpe(POST_CUTOFF_RETURNS, periods_per_year=252)
    assert contrast.pre_cutoff > contrast.post_cutoff
    assert contrast.overstatement == contrast.pre_cutoff - contrast.post_cutoff
    pre, post = contrast  # a NamedTuple: unpacking works
    assert (pre, post) == (contrast.pre_cutoff, contrast.post_cutoff)


def test_sharpe_contrast_uses_one_annualization_basis():
    yearly = contamination_sharpe_contrast(
        PRE_CUTOFF_RETURNS, POST_CUTOFF_RETURNS, periods_per_year=252
    )
    weekly = contamination_sharpe_contrast(
        PRE_CUTOFF_RETURNS, POST_CUTOFF_RETURNS, periods_per_year=52
    )
    assert yearly.pre_cutoff / weekly.pre_cutoff == pytest.approx((252 / 52) ** 0.5)
