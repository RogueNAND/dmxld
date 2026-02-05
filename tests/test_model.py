"""Tests for core model classes."""

import pytest

from dmxld.model import Fixture, FixtureGroup, FixtureState, FixtureType, Rig, Vec3
from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.color import Raw


RGBDimmer = FixtureType(DimmerAttr(), RGBAttr())
DimmerOnly = FixtureType(DimmerAttr())


class TestFixtureState:
    """Dict-based fixture state."""

    def test_dict_access(self) -> None:
        state = FixtureState(dimmer=0.5)
        state["pan"] = 0.25
        assert state["dimmer"] == 0.5
        assert state["pan"] == 0.25
        assert state.get("missing") is None

    def test_contains(self) -> None:
        state = FixtureState(dimmer=1.0)
        assert "dimmer" in state
        assert "rgb" not in state

    def test_copy_is_independent(self) -> None:
        state = FixtureState(dimmer=1.0)
        copy = state.copy()
        copy["dimmer"] = 0.5
        assert state.get("dimmer") == 1.0


class TestFixtureType:
    """Fixture type encoding."""

    def test_channel_count(self) -> None:
        assert RGBDimmer.channel_count == 4  # 1 dimmer + 3 RGB

    def test_encode(self) -> None:
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = RGBDimmer.encode(state)
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}

    def test_callable_creates_fixture(self) -> None:
        """FixtureType is callable and creates Fixture."""
        front = FixtureGroup()
        f = RGBDimmer(universe=1, address=10, groups={front})
        assert f.fixture_type is RGBDimmer
        assert f.universe == 1
        assert f.address == 10
        assert front in f.groups
        assert f in list(front)

    def test_default_groups(self) -> None:
        """FixtureType can have default groups."""
        front = FixtureGroup()
        FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})

        f = FrontPar(universe=1, address=1)
        assert front in f.groups
        assert f in list(front)

    def test_groups_are_additive(self) -> None:
        """Per-fixture groups add to default groups."""
        front = FixtureGroup()
        back = FixtureGroup()
        FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})

        f = FrontPar(universe=1, address=1, groups={back})
        assert front in f.groups  # default
        assert back in f.groups   # added


class TestFixture:
    """Fixture identity and hashing."""

    def test_identity_based_equality(self) -> None:
        """Same config doesn't mean same fixture."""
        f1 = Fixture(DimmerOnly, 1, 1)
        f2 = Fixture(DimmerOnly, 1, 1)
        assert f1 != f2
        assert f1 == f1

    def test_usable_as_dict_key(self) -> None:
        f1 = Fixture(DimmerOnly, 1, 1)
        f2 = Fixture(DimmerOnly, 1, 5)
        d = {f1: "first", f2: "second"}
        assert d[f1] == "first"
        assert d[f2] == "second"


class TestFixtureGroup:
    """FixtureGroup as selector and for grouping fixtures."""

    def test_group_collects_fixtures(self) -> None:
        front = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})
        f2 = Fixture(DimmerOnly, 1, 5, groups={front})

        assert len(front) == 2
        assert f1 in list(front)
        assert f2 in list(front)

    def test_fixture_in_multiple_groups(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front, back})

        assert f1 in list(front)
        assert f1 in list(back)

    def test_group_callable_as_selector(self) -> None:
        front = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})

        # Callable returns list of fixtures
        result = front(None)
        assert f1 in result

    def test_group_union(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})
        f2 = Fixture(DimmerOnly, 1, 5, groups={back})

        combined = front | back
        assert len(combined) == 2
        assert f1 in list(combined)
        assert f2 in list(combined)

    def test_group_intersection(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})
        f2 = Fixture(DimmerOnly, 1, 5, groups={front, back})
        f3 = Fixture(DimmerOnly, 1, 10, groups={back})

        overlap = front & back
        fixtures = list(overlap)
        assert len(fixtures) == 1
        assert f2 in fixtures
        assert f1 not in fixtures
        assert f3 not in fixtures


class TestRig:
    """Rig fixture selection and DMX encoding."""

    @pytest.fixture
    def rig(self) -> Rig:
        front = FixtureGroup()
        back = FixtureGroup()
        return Rig([
            Fixture(DimmerOnly, 1, 1, groups={front}),
            Fixture(DimmerOnly, 1, 10, groups={front}),
            Fixture(DimmerOnly, 1, 20, groups={back}),
        ])

    def test_all(self, rig: Rig) -> None:
        assert len(rig.all) == 3

    def test_encode_to_dmx(self, rig: Rig) -> None:
        states = {f: FixtureState(dimmer=1.0) for f in rig.all}
        dmx = rig.encode_to_dmx(states)

        assert dmx[1][1] == 255
        assert dmx[1][10] == 255
        assert dmx[1][20] == 255


class TestRigOverlapDetection:
    """Overlap detection for fixture channels within a universe."""

    def test_overlapping_fixtures_in_init_raises(self) -> None:
        """Two fixtures with overlapping channels should raise."""
        with pytest.raises(ValueError, match="overlaps"):
            Rig([
                Fixture(RGBDimmer, 1, 1),   # channels 1-4
                Fixture(RGBDimmer, 1, 3),   # channels 3-6, overlaps!
            ])

    def test_overlapping_fixtures_via_add_raises(self) -> None:
        """Adding an overlapping fixture should raise."""
        rig = Rig([Fixture(RGBDimmer, 1, 1)])  # channels 1-4
        with pytest.raises(ValueError, match="overlaps"):
            rig.add(Fixture(RGBDimmer, 1, 4))  # channels 4-7, overlaps at 4

    def test_adjacent_fixtures_ok(self) -> None:
        """Adjacent but non-overlapping fixtures should work."""
        rig = Rig([
            Fixture(RGBDimmer, 1, 1),   # channels 1-4
            Fixture(RGBDimmer, 1, 5),   # channels 5-8, adjacent ok
        ])
        assert len(rig.all) == 2

    def test_same_address_different_universe_ok(self) -> None:
        """Same address in different universes should not conflict."""
        rig = Rig([
            Fixture(RGBDimmer, 1, 1),
            Fixture(RGBDimmer, 2, 1),  # same address, different universe
        ])
        assert len(rig.all) == 2


from dmxld.attributes import RGBWAttr


class TestSegmentedFixtures:
    """Multi-segment fixture support."""

    def test_segmented_channel_count(self) -> None:
        """Segmented attribute multiplies channel count."""
        # 1 dimmer + 4 RGBW segments (4 channels each) = 17 channels
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        assert LEDBar.channel_count == 17

    def test_fixture_segment_count(self) -> None:
        """Fixture reports segment count from its type."""
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        fixture = Fixture(LEDBar, universe=1, address=1)
        assert fixture.segment_count == 4

    def test_non_segmented_fixture_count(self) -> None:
        """Non-segmented fixtures report segment_count=1."""
        fixture = Fixture(RGBDimmer, universe=1, address=1)
        assert fixture.segment_count == 1

    def test_encode_segmented_with_unified_color(self) -> None:
        """Single color applied to all segments."""
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = LEDBar.encode(state)

        # dimmer at offset 0
        assert encoded[0] == 255
        # Same color (red -> RGBW) for all 4 segments
        # RGBW conversion of pure red: (1.0, 0.0, 0.0) -> some RGBW values
        # All segments should be identical
        seg0 = [encoded[1], encoded[2], encoded[3], encoded[4]]
        seg1 = [encoded[5], encoded[6], encoded[7], encoded[8]]
        seg2 = [encoded[9], encoded[10], encoded[11], encoded[12]]
        seg3 = [encoded[13], encoded[14], encoded[15], encoded[16]]
        assert seg0 == seg1 == seg2 == seg3

    def test_encode_segmented_with_per_segment_colors(self) -> None:
        """Different colors per segment using indexed keys."""
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        state = FixtureState(
            dimmer=1.0,
            color_0=(1.0, 0.0, 0.0),  # red
            color_1=(0.0, 1.0, 0.0),  # green
            color_2=(0.0, 0.0, 1.0),  # blue
            color_3=(1.0, 1.0, 1.0),  # white
        )
        encoded = LEDBar.encode(state)

        # dimmer at offset 0
        assert encoded[0] == 255

        # Segment colors should be different
        seg0 = [encoded[1], encoded[2], encoded[3], encoded[4]]
        seg1 = [encoded[5], encoded[6], encoded[7], encoded[8]]
        seg2 = [encoded[9], encoded[10], encoded[11], encoded[12]]
        seg3 = [encoded[13], encoded[14], encoded[15], encoded[16]]

        # Verify they're not all the same
        assert seg0 != seg1
        assert seg1 != seg2
        assert seg2 != seg3

    def test_encode_segmented_with_raw(self) -> None:
        """Raw() wrapped values bypass conversion."""
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=2))
        state = FixtureState(
            dimmer=1.0,
            color_0=Raw(0.5, 0.0, 0.0, 0.0),
            color_1=Raw(0.0, 0.5, 0.0, 0.0),
        )
        encoded = LEDBar.encode(state)

        # Segment 0: R=127, G=0, B=0, W=0
        assert encoded[1] == 127
        assert encoded[2] == 0
        assert encoded[3] == 0
        assert encoded[4] == 0

        # Segment 1: R=0, G=127, B=0, W=0
        assert encoded[5] == 0
        assert encoded[6] == 127
        assert encoded[7] == 0
        assert encoded[8] == 0
