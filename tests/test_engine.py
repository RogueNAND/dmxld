"""Tests for DMXEngine rendering."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.blend import BlendOp, FixtureDelta
from dmxld.clips import Scene
from dmxld.engine import DMXEngine
from dmxld.model import Fixture, FixtureGroup, FixtureState, FixtureType, Rig


RGBFixture = FixtureType(DimmerAttr(), RGBAttr())


class TestRenderScene:
    def test_dmx_output(self) -> None:
        rig = Rig([Fixture(RGBFixture, universe=1, address=1)])
        engine = DMXEngine(rig=rig)

        scene = Scene(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0, color=(1.0, 1.0, 1.0)),
        )
        result = engine.render_scene(scene)

        assert result[1][1] == 255  # dimmer
        assert result[1][2] == 255  # red
        assert result[1][3] == 255  # green
        assert result[1][4] == 255  # blue

    def test_selector_filtering(self) -> None:
        left = FixtureGroup()
        right = FixtureGroup()
        rig = Rig([
            Fixture(RGBFixture, universe=1, address=1, groups={left}),
            Fixture(RGBFixture, universe=1, address=10, groups={right}),
        ])
        engine = DMXEngine(rig=rig)

        scene = Scene(
            selector=left,
            params=lambda f: FixtureState(dimmer=1.0),
        )
        result = engine.render_scene(scene)

        assert result[1][1] == 255   # left fixture lit
        assert result[1][10] == 0    # right fixture dark


class TestRenderDeltas:
    def test_applies_deltas(self) -> None:
        rig = Rig([Fixture(RGBFixture, universe=1, address=1)])
        engine = DMXEngine(rig=rig)
        fixture = rig.all[0]

        deltas = {fixture: FixtureDelta(dimmer=(BlendOp.SET, 1.0))}
        result = engine.render_deltas(deltas)

        assert result[1][1] == 255  # dimmer


class TestEngineLifecycle:
    def test_stop_without_start(self) -> None:
        engine = DMXEngine(rig=Rig([Fixture(RGBFixture, 1, 1)]))
        engine.stop()  # Should not raise

    def test_optional_rig(self) -> None:
        engine = DMXEngine()
        assert engine.rig is None

        rig = Rig([Fixture(RGBFixture, 1, 1)])
        engine.set_rig(rig)
        assert engine.rig is rig
