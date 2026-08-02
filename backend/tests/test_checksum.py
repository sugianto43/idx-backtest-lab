from app.domain.checksum import canonical_json_bytes, compute_checksum


def test_canonical_json_bytes_sorts_keys_regardless_of_input_order() -> None:
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}

    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_canonical_json_bytes_has_no_insignificant_whitespace() -> None:
    data = {"a": 1, "b": [1, 2, 3]}

    assert canonical_json_bytes(data) == b'{"a":1,"b":[1,2,3]}'


def test_compute_checksum_is_deterministic_for_equivalent_payloads() -> None:
    a = {"x": 1, "y": {"z": 2}}
    b = {"y": {"z": 2}, "x": 1}

    assert compute_checksum(a) == compute_checksum(b)


def test_compute_checksum_differs_for_materially_different_payloads() -> None:
    a = {"x": 1}
    b = {"x": 2}

    assert compute_checksum(a) != compute_checksum(b)


def test_compute_checksum_has_stable_prefix() -> None:
    assert compute_checksum({"a": 1}).startswith("sha256:")
