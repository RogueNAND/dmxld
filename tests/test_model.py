"""Unit tests for model classes."""

import pytest

from fcld.model import (
    Fixture,
    FixtureContext,
    FixtureState,
    FixtureType,
    GenericRGBDimmer,
    Rig,
    Vec3,
)


class TestVec3:
    """Tests for Vec3."""

    def test_defaults(self) -> None:
        """Default values are zero."""
        v = Vec3()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_custom_values(self) -> None:
        """Custom values are stored."""
        v = Vec3(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0


class TestFixtureState:
    """Tests for FixtureState."""

    def test_defaults(self) -> None:
        """Default values are zero/black."""
        state = FixtureState()
        assert state.dimmer == 0.0
        assert state.rgb == (0.0, 0.0, 0.0)

    def test_custom_values(self) -> None:
        """Custom values are stored."""
        state = FixtureState(dimmer=0.5, rgb=(1.0, 0.5, 0.25))
        assert state.dimmer == 0.5
        assert state.rgb == (1.0, 0.5, 0.25)


class TestGenericRGBDimmer:
    """Tests for GenericRGBDimmer fixture type."""

    def test_channel_count(self) -> None:
        """Has 4 channels."""
        ft = GenericRGBDimmer()
        assert ft.channel_count == 4

    def test_encode_full_white(self) -> None:
        """Full white encodes to 255 on all channels."""
        ft = GenericRGBDimmer()
        state = FixtureState(dimmer=1.0, rgb=(1.0, 1.0, 1.0))
        encoded = ft.encode(state)
        # Channel offsets: 0=dimmer, 1=R, 2=G, 3=B
        assert encoded == {0: 255, 1: 255, 2: 255, 3: 255}

    def test_encode_off(self) -> None:
        """Off state encodes to 0 on all channels."""
        ft = GenericRGBDimmer()
        state = FixtureState(dimmer=0.0, rgb=(0.0, 0.0, 0.0))
        encoded = ft.encode(state)
        assert encoded == {0: 0, 1: 0, 2: 0, 3: 0}

    def test_encode_half_dimmer(self) -> None:
        """Half dimmer encodes to 127."""
        ft = GenericRGBDimmer()
        state = FixtureState(dimmer=0.5, rgb=(1.0, 1.0, 1.0))
        encoded = ft.encode(state)
        assert encoded[0] == 127

    def test_encode_red(self) -> None:
        """Red color encodes correctly."""
        ft = GenericRGBDimmer()
        state = FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        # Channel offsets: 0=dimmer, 1=R, 2=G, 3=B
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}


class MockFixtureType(FixtureType):
    """Simple mock fixture type for Rig tests."""

    channel_count = 4

    @property
    def name(self) -> str:
        return "Mock"

    def encode(self, state: FixtureState) -> dict[int, int]:
        # Offset 0 = dimmer (like GenericRGBDimmer)
        return {0: int(state.dimmer * 255)}


class TestRig:
    """Tests for Rig."""

    @pytest.fixture
    def sample_rig(self) -> Rig:
        """Create a sample rig with multiple fixtures."""
        ft = MockFixtureType()
        fixtures = [
            Fixture(ft, 1, 1, Vec3(-1, 0, 0), {"side", "front"}),
            Fixture(ft, 1, 10, Vec3(1, 0, 0), {"side", "front"}),
            Fixture(ft, 1, 20, Vec3(0, 0, -1), {"back"}),
        ]
        return Rig(fixtures)

    def test_all_returns_all_fixtures(self, sample_rig: Rig) -> None:
        """all property returns all fixtures."""
        assert len(sample_rig.all) == 3

    def test_by_tag_returns_matching(self, sample_rig: Rig) -> None:
        """by_tag returns fixtures with tag."""
        fixtures = sample_rig.by_tag("side")
        assert len(fixtures) == 2

    def test_by_tag_no_matches(self, sample_rig: Rig) -> None:
        """by_tag returns empty list when no matches."""
        fixtures = sample_rig.by_tag("nonexistent")
        assert len(fixtures) == 0

    def test_encode_to_dmx(self, sample_rig: Rig) -> None:
        """encode_to_dmx produces correct DMX data."""
        states = {}
        for fixture in sample_rig.all:
            states[fixture] = FixtureState(dimmer=1.0)

        dmx = sample_rig.encode_to_dmx(states)

        assert 1 in dmx  # Universe 1
        # MockFixtureType only encodes dimmer at offset 0
        # So fixture at address 1 -> channel 1, address 10 -> channel 10, etc.
        assert dmx[1][1] == 255   # at address 1 + offset 0
        assert dmx[1][10] == 255  # at address 10 + offset 0
        assert dmx[1][20] == 255  # at address 20 + offset 0

    def test_encode_to_dmx_partial_states(self, sample_rig: Rig) -> None:
        """encode_to_dmx handles partial states."""
        first = sample_rig.all[0]
        states = {first: FixtureState(dimmer=0.5)}

        dmx = sample_rig.encode_to_dmx(states)

        assert dmx[1][1] == 127  # first at address 1 + offset 0
        # Others should not be present
        assert 10 not in dmx[1]
        assert 20 not in dmx[1]


class TestFixture:
    """Tests for Fixture."""

    def test_creation(self) -> None:
        """Fixture can be created with all parameters."""
        ft = MockFixtureType()
        fixture = Fixture(
            fixture_type=ft,
            universe=1,
            address=1,
            pos=Vec3(0, 0, 0),
            tags={"tag1", "tag2"},
        )
        assert fixture.universe == 1
        assert fixture.address == 1
        assert "tag1" in fixture.tags
        assert "tag2" in fixture.tags

    def test_identity_based_equality(self) -> None:
        """Two fixtures with same attributes are not equal (identity-based)."""
        ft = MockFixtureType()
        f1 = Fixture(ft, 1, 1)
        f2 = Fixture(ft, 1, 1)
        assert f1 != f2
        assert f1 == f1

    def test_identity_based_hash(self) -> None:
        """Different fixtures have different hashes."""
        ft = MockFixtureType()
        f1 = Fixture(ft, 1, 1)
        f2 = Fixture(ft, 1, 1)
        assert hash(f1) != hash(f2)

    def test_can_use_as_dict_key(self) -> None:
        """Fixtures can be used as dictionary keys."""
        ft = MockFixtureType()
        f1 = Fixture(ft, 1, 1)
        f2 = Fixture(ft, 1, 5)
        d = {f1: "first", f2: "second"}
        assert d[f1] == "first"
        assert d[f2] == "second"


class TestFixtureContext:
    """Tests for FixtureContext auto-collection."""

    def test_collects_fixtures(self) -> None:
        """Fixtures created in context are collected."""
        ft = MockFixtureType()
        with FixtureContext() as ctx:
            f1 = Fixture(ft, 1, 1)
            f2 = Fixture(ft, 1, 5)

        assert len(ctx.fixtures) == 2
        assert f1 in ctx.fixtures
        assert f2 in ctx.fixtures

    def test_context_isolation(self) -> None:
        """Fixtures outside context are not collected."""
        ft = MockFixtureType()
        f_outside = Fixture(ft, 1, 100)

        with FixtureContext() as ctx:
            f_inside = Fixture(ft, 1, 1)

        assert len(ctx.fixtures) == 1
        assert f_inside in ctx.fixtures
        assert f_outside not in ctx.fixtures

    def test_nested_contexts(self) -> None:
        """Nested contexts collect independently."""
        ft = MockFixtureType()
        with FixtureContext() as outer:
            f1 = Fixture(ft, 1, 1)
            with FixtureContext() as inner:
                f2 = Fixture(ft, 1, 5)
            f3 = Fixture(ft, 1, 10)

        assert len(inner.fixtures) == 1
        assert f2 in inner.fixtures

        assert len(outer.fixtures) == 2
        assert f1 in outer.fixtures
        assert f3 in outer.fixtures

    def test_empty_context(self) -> None:
        """Empty context returns empty list."""
        with FixtureContext() as ctx:
            pass

        assert ctx.fixtures == []
