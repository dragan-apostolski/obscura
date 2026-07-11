export type ChatProduct = {
  slug: string;
  name: string;
  brand: string;
  price_eur: number | null;
  in_stock: boolean;
  image: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  products?: ChatProduct[];
  sources?: string[];
  error?: boolean;
};
