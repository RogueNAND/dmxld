"""Unit tests for model classes."""

import pytest

from fcld.model import Fixture, FixtureState, FixtureType, GenericRGBDimmer, Rig, Vec3


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
            Fixture("left", ft, 1, 1, Vec3(-1, 0, 0), {"side", "front"}),
            Fixture("right", ft, 1, 10, Vec3(1, 0, 0), {"side", "front"}),
            Fixture("back", ft, 1, 20, Vec3(0, 0, -1), {"back"}),
        ]
        return Rig(fixtures)

    def test_all_returns_all_fixtures(self, sample_rig: Rig) -> None:
        """all property returns all fixtures."""
        assert len(sample_rig.all) == 3

    def test_by_name_found(self, sample_rig: Rig) -> None:
        """by_name returns fixture when found."""
        fixture = sample_rig.by_name("left")
        assert fixture is not None
        assert fixture.name == "left"

    def test_by_name_not_found(self, sample_rig: Rig) -> None:
        """by_name returns None when not found."""
        fixture = sample_rig.by_name("nonexistent")
        assert fixture is None

    def test_by_tag_returns_matching(self, sample_rig: Rig) -> None:
        """by_tag returns fixtures with tag."""
        fixtures = sample_rig.by_tag("side")
        assert len(fixtures) == 2
        names = {f.name for f in fixtures}
        assert names == {"left", "right"}

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
        assert dmx[1][1] == 255   # left at address 1 + offset 0
        assert dmx[1][10] == 255  # right at address 10 + offset 0
        assert dmx[1][20] == 255  # back at address 20 + offset 0

    def test_encode_to_dmx_partial_states(self, sample_rig: Rig) -> None:
        """encode_to_dmx handles partial states."""
        left = sample_rig.by_name("left")
        states = {left: FixtureState(dimmer=0.5)}

        dmx = sample_rig.encode_to_dmx(states)

        assert dmx[1][1] == 127  # left at address 1 + offset 0
        # Others should not be present
        assert 10 not in dmx[1]
        assert 20 not in dmx[1]


class TestFixture:
    """Tests for Fixture."""

    def test_creation(self) -> None:
        """Fixture can be created with all parameters."""
        ft = MockFixtureType()
        fixture = Fixture(
            name="test",
            fixture_type=ft,
            universe=1,
            address=1,
            pos=Vec3(0, 0, 0),
            tags={"tag1", "tag2"},
        )
        assert fixture.name == "test"
        assert fixture.universe == 1
        assert fixture.address == 1
        assert "tag1" in fixture.tags
        assert "tag2" in fixture.tags
