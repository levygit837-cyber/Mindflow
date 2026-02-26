import { LogViewer } from "@client/components/logs/log-viewer";

export default function LogsPage() {
  return (
    <div className="h-full flex flex-col">
      <LogViewer />
    </div>
  );
}
