export { default } from "next-auth/middleware";

// Protect these routes - users must be logged in to access them
export const config = {
  matcher: [
    "/collection/:path*",
    "/commander/:path*",
    "/deckbuilder/:path*",
    "/decks/:path*",
    "/import/:path*",
  ],
};
