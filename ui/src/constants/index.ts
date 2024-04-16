export const DraggableTypes = {
  PIECE: "piece",
};

export const API_URL =
  process.env.NODE_ENV === "production"
    ? "https://unichess-api-62644c9d9bf1.herokuapp.com"
    : "http://localhost:8000";

export const COOKIE_ATTRS = {
  expires: 1, // 1 day
  path: "/",
  domain:
    process.env.NODE_ENV === "production"
      ? "unichess.netlify.app"
      : "localhost",
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
};
