import { useEffect, useState } from "react";
import { CAREGIVERS } from "./caregivers.js";
import { CENTERS } from "./centers.js";
import { PRODUCTS } from "./products.js";

/*
 * Data-loading layer.
 *
 * Today these hooks resolve the local mock arrays synchronously (wrapped in an
 * effect so the shape is already async-friendly). When a real backend exists,
 * swap the body of each hook for a fetch() — the returned { data, loading, error }
 * contract stays identical, so no page/render code has to change.
 */

function useLocalCollection(collection) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Mock "load". Replace with: fetch(url).then(r => r.json())...
    let cancelled = false;
    try {
      if (!cancelled) {
        setData(collection);
        setLoading(false);
      }
    } catch (e) {
      if (!cancelled) {
        setError(e);
        setLoading(false);
      }
    }
    return () => {
      cancelled = true;
    };
  }, [collection]);

  return { data, loading, error };
}

export function useCaregivers() {
  return useLocalCollection(CAREGIVERS);
}

export function useCenters() {
  return useLocalCollection(CENTERS);
}

export function useProducts() {
  return useLocalCollection(PRODUCTS);
}
