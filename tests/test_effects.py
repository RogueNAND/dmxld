"""Tests for effect templates."""

import math

from dmxld import Fixture, FixtureGroup, FixtureType, Rig, DimmerAttr, RGBAttr
from dmxld.effects import (
    EffectTemplate,
    Pulse,
    Chase,
    Rainbow,
    Strobe,
    Wave,
    Solid,
)


DimmerOnly = FixtureType(DimmerAttr())
RGBDimmer = FixtureType(DimmerAttr(), RGBAttr())


class TestEffectTemplate:
    """EffectTemplate creates EffectClips."""

    def test_template_creates_clip(self) -> None:
        front = FixtureGroup()
        Fixture(DimmerOnly, 1, 1, groups={front})

        template = Pulse(rate=2.0)
        clip = template(front, duration=5.0)

        assert clip.duration == 5.0
        assert clip.selector is front

    def test_template_create_method(self) -> None:
        front = FixtureGroup()
        Fixture(DimmerOnly, 1, 1, groups={front})

        template = Pulse(rate=2.0)
        clip = template.create(front, duration=5.0, fade_in=1.0, fade_out=1.0)

        assert clip.duration == 5.0
        assert clip.fade_in == 1.0
        assert clip.fade_out == 1.0

    def test_template_attributes_accessible(self) -> None:
        """Parameters are accessible as attributes."""
        effect = Pulse(rate=3.0)
        assert effect.rate == 3.0

        effect2 = Chase(fixture_count=8, speed=2.0, width=1.5)
        assert effect2.fixture_count == 8
        assert effect2.speed == 2.0
        assert effect2.width == 1.5

    def test_template_name_property(self) -> None:
        """Effect name is derived from class and attributes."""
        effect = Pulse(rate=2.0)
        assert effect.name == "Pulse(rate=2.0)"

        effect2 = Strobe(rate=10.0, duty=0.3)
        assert effect2.name == "Strobe(rate=10.0, duty=0.3)"

    def test_template_repr(self) -> None:
        """Repr matches name."""
        effect = Pulse(rate=2.0)
        assert repr(effect) == "Pulse(rate=2.0)"


class TestPulseEffect:
    """Pulse effect produces sinusoidal dimmer values."""

    def test_pulse_at_zero(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        rig = Rig([f])

        clip = Pulse(rate=1.0)(front, duration=10.0)
        result = clip.render(0.0, rig)

        # sin(0) = 0, so 0.5 + 0.5*0 = 0.5
        assert f in result
        dimmer = result[f]["dimmer"][1]
        assert abs(dimmer - 0.5) < 0.01

    def test_pulse_at_quarter_period(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        rig = Rig([f])

        clip = Pulse(rate=1.0)(front, duration=10.0)
        result = clip.render(0.25, rig)

        # At t=0.25 with rate=1: sin(0.25 * 2 * pi) = 1
        # So 0.5 + 0.5*1 = 1.0
        dimmer = result[f]["dimmer"][1]
        assert abs(dimmer - 1.0) < 0.01


class TestChaseEffect:
    """Chase effect lights fixtures in sequence."""

    def test_chase_first_fixture(self) -> None:
        front = FixtureGroup()
        fixtures = [Fixture(DimmerOnly, 1, i * 5 + 1, groups={front}) for i in range(4)]
        rig = Rig(fixtures)

        clip = Chase(fixture_count=4, speed=1.0)(front, duration=10.0)
        result = clip.render(0.0, rig)

        # At t=0, position=0, first fixture should be brightest
        dimmer0 = result[fixtures[0]]["dimmer"][1]
        dimmer1 = result[fixtures[1]]["dimmer"][1]
        assert dimmer0 > dimmer1


class TestRainbowEffect:
    """Rainbow effect produces cycling colors."""

    def test_rainbow_has_rgb(self) -> None:
        front = FixtureGroup()
        f = Fixture(RGBDimmer, 1, 1, groups={front})
        rig = Rig([f])

        clip = Rainbow(speed=0.5)(front, duration=10.0)
        result = clip.render(0.0, rig)

        assert "rgb" in result[f]
        assert "dimmer" in result[f]


class TestStrobeEffect:
    """Strobe effect produces on/off pattern."""

    def test_strobe_on_phase(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        rig = Rig([f])

        clip = Strobe(rate=10.0, duty=0.5)(front, duration=10.0)
        result = clip.render(0.0, rig)

        # At t=0, phase=0, should be on (phase < duty)
        dimmer = result[f]["dimmer"][1]
        assert dimmer == 1.0

    def test_strobe_off_phase(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        rig = Rig([f])

        clip = Strobe(rate=10.0, duty=0.5)(front, duration=10.0)
        # At t=0.06, rate=10: phase = (0.06 * 10) % 1 = 0.6
        # 0.6 >= 0.5, should be off
        result = clip.render(0.06, rig)

        dimmer = result[f]["dimmer"][1]
        assert dimmer == 0.0


class TestWaveEffect:
    """Wave effect produces traveling dimmer wave."""

    def test_wave_varies_by_index(self) -> None:
        front = FixtureGroup()
        fixtures = [Fixture(DimmerOnly, 1, i * 5 + 1, groups={front}) for i in range(4)]
        rig = Rig(fixtures)

        clip = Wave(speed=1.0, wavelength=4.0)(front, duration=10.0)
        result = clip.render(0.0, rig)

        # Different fixtures should have different dimmer values
        dimmers = [result[f]["dimmer"][1] for f in fixtures]
        assert len(set(dimmers)) > 1


class TestSolidEffect:
    """Solid effect produces static output."""

    def test_solid_dimmer(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        rig = Rig([f])

        clip = Solid(dimmer=0.75)(front, duration=10.0)
        result = clip.render(5.0, rig)

        dimmer = result[f]["dimmer"][1]
        assert dimmer == 0.75

    def test_solid_with_rgb(self) -> None:
        front = FixtureGroup()
        f = Fixture(RGBDimmer, 1, 1, groups={front})
        rig = Rig([f])

        clip = Solid(dimmer=1.0, rgb=(1.0, 0.0, 0.5))(front, duration=10.0)
        result = clip.render(0.0, rig)

        assert result[f]["dimmer"][1] == 1.0
        assert result[f]["rgb"][1] == (1.0, 0.0, 0.5)
