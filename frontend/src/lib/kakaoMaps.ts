let loader: Promise<void> | null = null;

export function loadKakaoMaps(): Promise<void> {
  if (window.kakao?.maps) return new Promise((resolve) => window.kakao.maps.load(resolve));
  if (loader) return loader;
  loader = new Promise((resolve, reject) => {
    const key = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY?.trim();
    if (!key) { reject(new Error("카카오 지도 JavaScript 키가 설정되지 않았습니다.")); return; }
    const existing = document.querySelector<HTMLScriptElement>('script[data-seoullo-kakao-map="true"]');
    if (existing) {
      existing.addEventListener("load", () => window.kakao.maps.load(resolve), { once: true });
      existing.addEventListener("error", () => reject(new Error("카카오 지도를 불러오지 못했습니다.")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.dataset.seoulloKakaoMap = "true";
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(key)}&autoload=false&libraries=services,clusterer`;
    script.onload = () => window.kakao.maps.load(resolve);
    script.onerror = () => reject(new Error("카카오 지도를 불러오지 못했습니다."));
    document.head.appendChild(script);
  });
  return loader;
}

