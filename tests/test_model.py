"""Tests for core model classes."""

import pytest

from dmxld.model import Fixture, FixtureState, FixtureType, Rig, Vec3
from dmxld.attributes import DimmerAttr, RGBAttr


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
        state = FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))
        encoded = RGBDimmer.encode(state)
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}


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


class TestRig:
    """Rig fixture selection and DMX encoding."""

    @pytest.fixture
    def rig(self) -> Rig:
        return Rig([
            Fixture(DimmerOnly, 1, 1, tags={"front"}),
            Fixture(DimmerOnly, 1, 10, tags={"front"}),
            Fixture(DimmerOnly, 1, 20, tags={"back"}),
        ])

    def test_all(self, rig: Rig) -> None:
        assert len(rig.all) == 3

    def test_by_tag(self, rig: Rig) -> None:
        assert len(rig.by_tag("front")) == 2
        assert len(rig.by_tag("nonexistent")) == 0

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
