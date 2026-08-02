export function PaginationControls({
  limit,
  offset,
  total,
  onPrevious,
  onNext,
}: {
  limit: number;
  offset: number;
  total: number;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <nav aria-label="Pagination">
      <p>
        Page {page} of {pageCount} ({total} total)
      </p>
      <button type="button" onClick={onPrevious} disabled={offset === 0}>
        Previous
      </button>
      <button type="button" onClick={onNext} disabled={offset + limit >= total}>
        Next
      </button>
    </nav>
  );
}
