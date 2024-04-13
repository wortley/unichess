export const DraggableTypes = {
  PIECE: "piece",
};

export const API_URL =
  process.env.NODE_ENV === "production"
    ? "https://unichess-api-62644c9d9bf1.herokuapp.com"
    : "http://localhost:8000";
