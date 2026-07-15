import type {
  CategoryCount,
  ChatHistoryMessage,
  ChatResponse,
  AddressSearchResult,
  DuplicateWarning,
  EmotionCheckinRequest,
  EmotionCheckinResponse,
  EmotionRecommendationRequest,
  EmotionRecommendationResponse,
  PlaceDetail,
  PlaceList,
  PlaceMapPoint,
  PlaceMapQuery,
  PlaceQuery,
  PopularTag,
  Review,
  ReviewList,
  ReverseGeocodeResult,
} from "../types/place";

const apiOrigin = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "요청을 처리하지 못했습니다.");
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiOrigin}${path}`, {
    ...options,
    headers: options?.body instanceof FormData
      ? options.headers
      : { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "서버 응답을 확인할 수 없습니다." }));
    throw new ApiError(response.status, payload.detail ?? payload);
  }
  return response.json() as Promise<T>;
}

export function mediaUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return value;
  return `${apiOrigin}${value}`;
}

export function getPlaces(query: PlaceQuery = {}): Promise<PlaceList> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, Array.isArray(value) ? value.join(",") : String(value));
    }
  });
  return request<PlaceList>(`/api/places?${params.toString()}`);
}

export function getCategories(): Promise<CategoryCount[]> {
  return request<CategoryCount[]>("/api/places/categories");
}

export function getMapPoints(query: PlaceMapQuery): Promise<PlaceMapPoint[]> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, Array.isArray(value) ? value.join(",") : String(value));
    }
  });
  return request<PlaceMapPoint[]>(`/api/places/map-points?${params.toString()}`);
}

export function getPlace(id: number | string): Promise<PlaceDetail> {
  return request<PlaceDetail>(`/api/places/${id}`);
}

export function createPlace(form: FormData): Promise<PlaceDetail> {
  return request<PlaceDetail>("/api/places", { method: "POST", body: form });
}

export function updatePlace(id: number | string, form: FormData): Promise<PlaceDetail> {
  return request<PlaceDetail>(`/api/places/${id}`, { method: "PUT", body: form });
}

export function deletePlace(id: number | string, password: string): Promise<{ deleted: boolean; id: number }> {
  return request(`/api/places/${id}`, {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });
}

export function deletePlaceImage(
  placeId: number | string,
  imageId: number,
  password: string,
): Promise<{ deleted: boolean; id: number }> {
  return request(`/api/places/${placeId}/images/${imageId}`, {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });
}

export function duplicateWarning(error: unknown): DuplicateWarning | null {
  if (!(error instanceof ApiError) || error.status !== 409 || typeof error.detail !== "object" || !error.detail) {
    return null;
  }
  const detail = error.detail as Partial<DuplicateWarning>;
  return detail.code === "DUPLICATE_PLACE_WARNING" ? (detail as DuplicateWarning) : null;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (typeof error.detail === "object" && error.detail && "message" in error.detail) {
      return String((error.detail as { message: unknown }).message);
    }
  }
  return error instanceof Error ? error.message : "예상하지 못한 오류가 발생했습니다.";
}

export function getPopularTags(): Promise<PopularTag[]> {
  return request<PopularTag[]>("/api/tags/popular");
}

export function getReviews(
  placeId: number | string,
  sort: "latest" | "likes" | "rating" = "latest",
  page = 1,
): Promise<ReviewList> {
  return request<ReviewList>(`/api/places/${placeId}/reviews?sort=${sort}&page=${page}&size=20`);
}

export function createReview(
  placeId: number | string,
  payload: { rating: number; content: string; password: string },
): Promise<Review> {
  return request<Review>(`/api/places/${placeId}/reviews`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateReview(
  reviewId: number,
  payload: { rating: number; content: string; password: string },
): Promise<Review> {
  return request<Review>(`/api/reviews/${reviewId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteReview(reviewId: number, password: string): Promise<{ deleted: boolean; id: number }> {
  return request(`/api/reviews/${reviewId}`, {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });
}

export function togglePlaceLike(placeId: number | string): Promise<{ liked: boolean; like_count: number }> {
  return request(`/api/places/${placeId}/like`, { method: "POST" });
}

export function toggleReviewLike(reviewId: number): Promise<{ liked: boolean; like_count: number }> {
  return request(`/api/reviews/${reviewId}/like`, { method: "POST" });
}

export function incrementPlaceView(placeId: number | string): Promise<{ view_count: number }> {
  return request(`/api/places/${placeId}/view`, { method: "POST" });
}


export function searchKakaoAddress(query: string): Promise<AddressSearchResult[]> {
  return request<AddressSearchResult[]>(`/api/maps/address-search?q=${encodeURIComponent(query)}`);
}

export function reverseGeocode(latitude: number, longitude: number): Promise<ReverseGeocodeResult> {
  const params = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude) });
  return request<ReverseGeocodeResult>(`/api/maps/reverse-geocode?${params.toString()}`);
}

export function getEmotionRecommendations(
  payload: EmotionRecommendationRequest,
): Promise<EmotionRecommendationResponse> {
  return request<EmotionRecommendationResponse>("/api/emotions/recommendations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createEmotionCheckin(
  payload: EmotionCheckinRequest,
): Promise<EmotionCheckinResponse> {
  return request<EmotionCheckinResponse>("/api/emotions/checkins", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sendChatMessage(
  message: string,
  history: ChatHistoryMessage[],
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat/messages", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
