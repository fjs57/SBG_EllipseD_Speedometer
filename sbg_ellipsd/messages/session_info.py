from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogSessionInfo:
    """Paginated JSON session metadata (MSG 0x37).

    Reassemble the full JSON by concatenating ``data`` across all chunks
    ordered by ``page_index``.
    """

    page_index: int
    page_count: int
    data_size: int
    data: bytes
    """Raw JSON chunk — decode as UTF-8 and concatenate pages to get the full document."""
