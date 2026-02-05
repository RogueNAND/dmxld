"""Tests for effect templates."""

import pytest

from dmxld import Fixture, FixtureGroup, FixtureType, Rig, DimmerAttr, RGBAttr
from dmxld.effects import Pulse, Chase, Rainbow, Strobe, Wave, Solid


DimmerOnly = FixtureType(DimmerAttr())
RGBDimmer = FixtureType(DimmerAttr(), RGBAttr())


class TestEffectTemplate:
    def test_creates_clip(self) -> None:
        front = FixtureGroup()
        Fixture(DimmerOnly, 1, 1, groups={front})

        clip = Pulse(rate=2.0)(front, duration=5.0)
        assert clip.duration == 5.0
        assert clip.selector is front

    def test_create_with_fades(self) -> None:
        front = FixtureGroup()
        Fixture(DimmerOnly, 1, 1, groups={front})

        clip = Pulse(rate=2.0).create(front, duration=5.0, fade_in=1.0, fade_out=1.0)
        assert clip.fade_in == 1.0
        assert clip.fade_out == 1.0

    def test_attributes_accessible(self) -> None:
        assert Pulse(rate=3.0).rate == 3.0
        assert Chase(fixture_count=8, speed=2.0).fixture_count == 8

    def test_name_and_repr(self) -> None:
        effect = Pulse(rate=2.0)
        assert effect.name == "Pulse(rate=2.0)"
        assert repr(effect) == "Pulse(rate=2.0)"


class TestBuiltInEffects:
    @pytest.fixture
    def setup(self):
        """Create common test fixtures."""
        front = FixtureGroup()
        fixtures = [Fixture(DimmerOnly, 1, i * 5 + 1, groups={front}) for i in range(4)]
        rig = Rig(fixtures)
        return front, fixtures, rig

    def test_pulse_sine_wave(self, setup) -> None:
        front, fixtures, rig = setup
        clip = Pulse(rate=1.0)(front, duration=10.0)

        # sin(0) = 0 → dimmer = 0.5
        result = clip.render(0.0, rig)
        assert result[fixtures[0]]["dimmer"][1] == pytest.approx(0.5, abs=0.01)

        # sin(π/2) = 1 → dimmer = 1.0
        result = clip.render(0.25, rig)
        assert result[fixtures[0]]["dimmer"][1] == pytest.approx(1.0, abs=0.01)

    def test_chase_sequence(self, setup) -> None:
        front, fixtures, rig = setup
        clip = Chase(fixture_count=4, speed=1.0)(front, duration=10.0)
        result = clip.render(0.0, rig)

        # First fixture should be brightest at t=0
        assert result[fixtures[0]]["dimmer"][1] > result[fixtures[1]]["dimmer"][1]

    def test_rainbow_color(self) -> None:
        front = FixtureGroup()
        f = Fixture(RGBDimmer, 1, 1, groups={front})
        rig = Rig([f])

        clip = Rainbow(speed=1.0)(front, duration=10.0)
        result_t0 = clip.render(0.0, rig)
        result_t1 = clip.render(0.5, rig)

        assert "color" in result_t0[f]
        assert result_t0[f]["color"][1] != result_t1[f]["color"][1]

    def test_strobe_on_off(self, setup) -> None:
        front, fixtures, rig = setup
        clip = Strobe(rate=10.0, duty=0.5)(front, duration=10.0)

        # t=0, phase=0 → on
        assert clip.render(0.0, rig)[fixtures[0]]["dimmer"][1] == 1.0
        # t=0.06, phase=0.6 → off
        assert clip.render(0.06, rig)[fixtures[0]]["dimmer"][1] == 0.0

    def test_wave_varies_by_index(self, setup) -> None:
        front, fixtures, rig = setup
        clip = Wave(speed=1.0, wavelength=4.0)(front, duration=10.0)
        result = clip.render(0.0, rig)

        dimmers = [result[f]["dimmer"][1] for f in fixtures]
        assert len(set(dimmers)) > 1

    def test_solid_static(self) -> None:
        front = FixtureGroup()
        f = Fixture(RGBDimmer, 1, 1, groups={front})
        rig = Rig([f])

        clip = Solid(dimmer=0.75, color=(1.0, 0.0, 0.5))(front, duration=10.0)
        result = clip.render(5.0, rig)

        assert result[f]["dimmer"][1] == 0.75
        assert result[f]["color"][1] == (1.0, 0.0, 0.5)
