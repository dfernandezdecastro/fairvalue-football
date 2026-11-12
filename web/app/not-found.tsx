import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg space-y-4 py-16 text-center">
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="text-sm text-muted-foreground">
        This player, club or page isn&apos;t in the dataset. Coverage: 14 European top flights, 2015/16 to 2025/26.
      </p>
      <Link href="/" className="text-sm underline underline-offset-2">
        Back to the overview
      </Link>
    </div>
  );
}
