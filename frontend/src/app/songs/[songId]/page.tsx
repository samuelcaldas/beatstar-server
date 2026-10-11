import SongDetailPage from "./song-detail-page";

/**
 * Generates the shell required by Next's static exporter.
 * The client component resolves the actual song through the admin API.
 */
export function generateStaticParams(): Array<{ songId: string }> {
  return [{ songId: "preview" }];
}

export default function SongDetailRoute() {
  return <SongDetailPage />;
}
