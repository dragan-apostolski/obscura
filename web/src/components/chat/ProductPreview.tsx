"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRightIcon } from "@phosphor-icons/react";
import { formatPrice } from "@/lib/format";
import type { ChatProduct } from "./types";

export function ProductPreview({ product, index }: { product: ChatProduct; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20, delay: index * 0.08 }}
    >
      <Link
        href={`/products/${product.slug}`}
        className="group flex items-center gap-3 rounded-2xl border border-line bg-background p-2.5 transition-colors hover:border-foreground/25 active:scale-[0.99]"
      >
        <div className="relative h-16 w-20 shrink-0 overflow-hidden rounded-xl bg-card">
          <Image
            src={product.image}
            alt={product.name}
            fill
            sizes="80px"
            className="object-contain p-1.5 mix-blend-multiply"
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] uppercase tracking-[0.14em] text-faint">
            {product.brand}
          </p>
          <p className="truncate text-sm font-medium">{product.name}</p>
          <div className="mt-0.5 flex items-center gap-2.5">
            <span className="font-mono text-xs text-foreground/80">
              {formatPrice(product.price_eur)}
            </span>
            <span className="flex items-center gap-1 text-[11px] text-faint">
              <span
                className={`h-1 w-1 rounded-full ${
                  product.in_stock ? "bg-emerald-500" : "bg-stone-300"
                }`}
              />
              {product.in_stock ? "In stock" : "Back-order"}
            </span>
          </div>
        </div>
        <ArrowRightIcon
          size={16}
          className="mr-1.5 shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-foreground"
        />
      </Link>
    </motion.div>
  );
}
