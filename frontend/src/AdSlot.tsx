import { useEffect } from "react";

declare global { interface Window { adsbygoogle?: unknown[] } }

/** Google AdSense slot. Add the AdSense <script> to index.html after approval and replace the IDs. */
export default function AdSlot({ slot }: { slot: string }) {
  useEffect(() => { try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch {} }, []);
  return (
    <aside className="ad" aria-label="Advertisement">
      <ins className="adsbygoogle" style={{ display: "block" }} data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
           data-ad-slot={slot} data-ad-format="auto" data-full-width-responsive="true" />
    </aside>
  );
}
