import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.database import DailyUsage, Trip
from app.planner.destination import city_input_error
from test_durable_trips import system, OWNER, wait_run
from test_planner_graph import make_request, valid_plan_json


@pytest.mark.parametrize('value', ['云南', '云南省', '广西壮族自治区', '内蒙古自治区'])
def test_province_requires_explicit_city(value):
    assert '具体城市' in city_input_error(value)


@pytest.mark.parametrize('value', ['昆明', '丽江市', '北京', '重庆', '大理白族自治州'])
def test_cities_are_accepted(value):
    assert city_input_error(value) is None


def test_invalid_destination_does_not_create_task_or_consume_daily_quota(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            with pytest.raises(HTTPException) as error:
                await runs.create(OWNER, make_request().model_copy(update={'city': '云南'}), str(uuid4()))
            assert error.value.status_code == 422
            assert error.value.detail['code'] == 'DESTINATION_REQUIRES_CITY'
            assert not runs.tasks
            async with runs.sessions() as session:
                assert await session.scalar(select(func.count()).select_from(Trip)) == 0
                assert await session.scalar(select(func.count()).select_from(DailyUsage)) == 0
    asyncio.run(scenario())


def test_mismatched_model_destination_has_visible_reason(tmp_path):
    import json
    from app.database import TripEvent
    async def scenario():
        wrong = json.loads(valid_plan_json())
        wrong['city'] = '昆明'
        async with system(tmp_path, [json.dumps(wrong)]) as runs:
            created = await runs.create(OWNER, make_request(), str(uuid4()))
            result = await wait_run(runs, created['id'])
            assert result.status == 'fallback' and '目的地' in result.message
            async with runs.sessions() as session:
                events = (await session.scalars(select(TripEvent))).all()
                failed = [e.payload for e in events if e.payload['type'] == 'validation.failed']
                assert failed and all(e['error_code'] == 'DESTINATION_MISMATCH' for e in failed)
                assert all('目的地' in e['label'] for e in failed)
    asyncio.run(scenario())
