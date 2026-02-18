"""Tests for core model classes."""

import pytest

from dmxld.model import Fixture, FixtureGroup, FixtureState, FixtureType, Rig
from dmxld.attributes import DimmerAttr, RGBAttr, RGBWAttr
from dmxld.color import Raw


RGBDimmer = FixtureType(DimmerAttr(), RGBAttr())
DimmerOnly = FixtureType(DimmerAttr())


class TestFixtureState:
    def test_dict_behavior(self) -> None:
        state = FixtureState(dimmer=0.5)
        state["pan"] = 0.25

        assert state["dimmer"] == 0.5
        assert state["pan"] == 0.25
        assert "dimmer" in state
        assert "missing" not in state
        assert state.get("missing") is None

    def test_copy_is_independent(self) -> None:
        state = FixtureState(dimmer=1.0)
        copy = state.copy()
        copy["dimmer"] = 0.5
        assert state["dimmer"] == 1.0


class TestFixtureType:
    def test_channel_count(self) -> None:
        assert RGBDimmer.channel_count == 4

    def test_encode(self) -> None:
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        assert RGBDimmer.encode(state) == {0: 255, 1: 255, 2: 0, 3: 0}

    def test_callable_creates_fixture(self) -> None:
        front = FixtureGroup()
        f = RGBDimmer(universe=1, address=10, groups={front})

        assert f.fixture_type is RGBDimmer
        assert f.universe == 1
        assert f.address == 10
        assert front in f.groups
        assert f in list(front)

    def test_default_groups(self) -> None:
        front = FixtureGroup()
        FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})
        f = FrontPar(universe=1, address=1)

        assert front in f.groups
        assert f in list(front)

    def test_groups_are_additive(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})
        f = FrontPar(universe=1, address=1, groups={back})

        assert front in f.groups
        assert back in f.groups


class TestFixture:
    def test_identity_based_equality(self) -> None:
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
    def test_group_label(self) -> None:
        g = FixtureGroup("Location")
        assert g.group == "Location"

    def test_group_label_default_none(self) -> None:
        g = FixtureGroup()
        assert g.group is None

    def test_collects_fixtures(self) -> None:
        front = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})
        f2 = Fixture(DimmerOnly, 1, 5, groups={front})

        assert len(front) == 2
        assert f1 in list(front)
        assert f2 in list(front)

    def test_multiple_groups(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front, back})

        assert f in list(front)
        assert f in list(back)

    def test_callable_as_selector(self) -> None:
        front = FixtureGroup()
        f = Fixture(DimmerOnly, 1, 1, groups={front})
        assert f in front(None)

    def test_union_and_intersection(self) -> None:
        front = FixtureGroup()
        back = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={front})
        f2 = Fixture(DimmerOnly, 1, 5, groups={front, back})
        f3 = Fixture(DimmerOnly, 1, 10, groups={back})

        combined = front | back
        assert len(combined) == 3

        overlap = front & back
        assert list(overlap) == [f2]


class TestFixtureAsSelector:
    def test_iterable(self) -> None:
        f = Fixture(DimmerOnly, 1, 1)
        assert list(f) == [f]

    def test_len(self) -> None:
        f = Fixture(DimmerOnly, 1, 1)
        assert len(f) == 1

    def test_callable(self) -> None:
        f = Fixture(DimmerOnly, 1, 1)
        assert f(None) == [f]


class TestFixtureGroupOperators:
    def test_fixture_plus_fixture(self) -> None:
        f1 = Fixture(DimmerOnly, 1, 1)
        f2 = Fixture(DimmerOnly, 1, 5)
        group = f1 + f2
        assert isinstance(group, FixtureGroup)
        assert set(group) == {f1, f2}

    def test_fixture_plus_group(self) -> None:
        g = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={g})
        f2 = Fixture(DimmerOnly, 1, 5)
        result = f2 + g
        assert isinstance(result, FixtureGroup)
        assert set(result) == {f1, f2}

    def test_group_plus_fixture(self) -> None:
        g = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={g})
        f2 = Fixture(DimmerOnly, 1, 5)
        result = g + f2
        assert isinstance(result, FixtureGroup)
        assert set(result) == {f1, f2}

    def test_fixture_or(self) -> None:
        f1 = Fixture(DimmerOnly, 1, 1)
        f2 = Fixture(DimmerOnly, 1, 5)
        assert set(f1 | f2) == {f1, f2}

    def test_fixture_and(self) -> None:
        g = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={g})
        f2 = Fixture(DimmerOnly, 1, 5)
        assert set(f1 & g) == {f1}
        assert set(f2 & g) == set()

    def test_fixture_sub(self) -> None:
        g = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={g})
        f2 = Fixture(DimmerOnly, 1, 5, groups={g})
        result = g - f1
        assert set(result) == {f2}

    def test_fixture_xor(self) -> None:
        g = FixtureGroup()
        f1 = Fixture(DimmerOnly, 1, 1, groups={g})
        f2 = Fixture(DimmerOnly, 1, 5)
        result = f1 ^ g  # f1 is in both, so excluded
        assert set(result) == set()
        result = f2 ^ g  # f2 not in g, f1 in g
        assert set(result) == {f1, f2}


class TestRig:
    def test_all_and_encode(self) -> None:
        rig = Rig([
            Fixture(DimmerOnly, 1, 1),
            Fixture(DimmerOnly, 1, 10),
            Fixture(DimmerOnly, 1, 20),
        ])
        assert len(rig.all) == 3

        states = {f: FixtureState(dimmer=1.0) for f in rig.all}
        dmx = rig.encode_to_dmx(states)
        assert dmx[1][1] == 255
        assert dmx[1][10] == 255
        assert dmx[1][20] == 255


class TestRigOverlapDetection:
    def test_overlapping_raises(self) -> None:
        with pytest.raises(ValueError, match="overlaps"):
            Rig([
                Fixture(RGBDimmer, 1, 1),
                Fixture(RGBDimmer, 1, 3),
            ])

    def test_overlapping_via_add_raises(self) -> None:
        rig = Rig([Fixture(RGBDimmer, 1, 1)])
        with pytest.raises(ValueError, match="overlaps"):
            rig.add(Fixture(RGBDimmer, 1, 4))

    def test_adjacent_ok(self) -> None:
        rig = Rig([
            Fixture(RGBDimmer, 1, 1),
            Fixture(RGBDimmer, 1, 5),
        ])
        assert len(rig.all) == 2

    def test_same_address_different_universe_ok(self) -> None:
        rig = Rig([
            Fixture(RGBDimmer, 1, 1),
            Fixture(RGBDimmer, 2, 1),
        ])
        assert len(rig.all) == 2


class TestSegmentedFixtures:
    def test_segment_count(self) -> None:
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        assert LEDBar.channel_count == 17

        fixture = Fixture(LEDBar, universe=1, address=1)
        assert fixture.segment_count == 4

        # Non-segmented
        assert Fixture(RGBDimmer, 1, 1).segment_count == 1

    def test_encode_unified_color(self) -> None:
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = LEDBar.encode(state)

        # All segments get same color
        seg0 = [encoded[1], encoded[2], encoded[3], encoded[4]]
        seg1 = [encoded[5], encoded[6], encoded[7], encoded[8]]
        assert seg0 == seg1

    def test_encode_per_segment_colors(self) -> None:
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        state = FixtureState(
            dimmer=1.0,
            color_0=(1.0, 0.0, 0.0),
            color_1=(0.0, 1.0, 0.0),
            color_2=(0.0, 0.0, 1.0),
            color_3=(1.0, 1.0, 1.0),
        )
        encoded = LEDBar.encode(state)

        seg0 = [encoded[1], encoded[2], encoded[3], encoded[4]]
        seg1 = [encoded[5], encoded[6], encoded[7], encoded[8]]
        assert seg0 != seg1

    def test_encode_raw_bypasses_conversion(self) -> None:
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=2))
        state = FixtureState(
            dimmer=1.0,
            color_0=Raw(0.5, 0.0, 0.0, 0.0),
            color_1=Raw(0.0, 0.5, 0.0, 0.0),
        )
        encoded = LEDBar.encode(state)

        assert encoded[1] == 127  # R seg0
        assert encoded[5] == 0    # R seg1
        assert encoded[6] == 127  # G seg1
