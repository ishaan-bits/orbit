import { FileSearch, FolderPlus, SearchX } from "lucide-react";

interface EmptyStateProps {
  variant: "empty" | "search" | "folder";
  query?: string;
  folderName?: string;
}

function Illustration() {
  return (
    <svg
      viewBox="0 0 260 170"
      role="img"
      aria-label="Documents illustration"
      className="mx-auto h-36 w-auto text-border"
    >
      <rect
        x="70"
        y="30"
        width="100"
        height="120"
        rx="8"
        fill="currentColor"
        opacity="0.35"
        transform="rotate(6 120 90)"
      />
      <rect
        x="82"
        y="26"
        width="100"
        height="120"
        rx="8"
        fill="currentColor"
        opacity="0.55"
        transform="rotate(-3 132 86)"
      />
      <rect
        x="88"
        y="22"
        width="100"
        height="120"
        rx="8"
        className="fill-card"
        stroke="currentColor"
        strokeWidth="2"
      />
      <line
        x1="104"
        y1="48"
        x2="172"
        y2="48"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="104"
        y1="66"
        x2="172"
        y2="66"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        opacity="0.7"
      />
      <line
        x1="104"
        y1="84"
        x2="150"
        y2="84"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        opacity="0.5"
      />
      <circle
        cx="186"
        cy="118"
        r="26"
        className="fill-card"
        stroke="currentColor"
        strokeWidth="3"
      />
      <line
        x1="205"
        y1="137"
        x2="224"
        y2="156"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <line
        x1="176"
        y1="118"
        x2="196"
        y2="118"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <line
        x1="186"
        y1="108"
        x2="186"
        y2="128"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function EmptyState({ variant, query, folderName }: EmptyStateProps) {
  const content = {
    empty: {
      icon: FolderPlus,
      title: "No documents yet",
      description:
        "Upload PDFs, Word documents, text files or Markdown to start building your knowledge base.",
    },
    search: {
      icon: SearchX,
      title: "No matching documents",
      description: query
        ? `Nothing matches “${query}”. Try a different search term.`
        : "Try a different search term.",
    },
    folder: {
      icon: FileSearch,
      title: "This folder is empty",
      description: folderName
        ? `No documents in “${folderName}” yet. Drop files here to add them.`
        : "No documents in this folder yet.",
    },
  }[variant];

  const Icon = content.icon;

  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-12 text-center">
      <Illustration />
      <div className="mt-4 flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-foreground">
        {content.title}
      </h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        {content.description}
      </p>
    </div>
  );
}
