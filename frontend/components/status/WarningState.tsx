export function WarningState({ message }: { message: string }) {
  return (
    <p role="status" className="warning-state">
      <strong>Warning: </strong>
      {message}
    </p>
  );
}
