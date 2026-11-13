import type { MetadataRoute } from "next";

// Public pages are indexable; the internal component review page and the API aren't.
export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: "*", allow: "/", disallow: ["/design", "/api/"] } };
}
