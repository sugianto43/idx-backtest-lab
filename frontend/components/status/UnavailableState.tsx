export function UnavailableState({ message }: { message: string }) {
  return (
    <p role="status" className="unavailable-state">
      {message}
    </p>
  );
}
