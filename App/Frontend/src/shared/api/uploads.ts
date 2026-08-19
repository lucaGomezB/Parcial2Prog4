/**
 * Uploads API — Cloudinary image upload and deletion.
 *
 * All functions delegate to the shared `apiClient` (Axios) for direct
 * access (multipart FormData bypass) and `apiFetch` for JSON endpoints.
 *
 * Error handling convention: callers wrap in try/catch. The axios response
 * interceptor handles 401 auto-refresh. Other HTTP errors are thrown as
 * AxiosError for the caller.
 */
import apiClient, { apiFetch } from "@/shared/api/client";

// ── Types ──

export interface ImageUploadResponse {
  secure_url: string;
  public_id: string;
}

export const uploadsApi = {
  /**
   * Uploads an image file to Cloudinary via the server-side endpoint.
   *
   * Uses `apiClient` directly (not `apiFetch`) because `apiFetch` tries
   * to JSON-parse the body, which fails for FormData multipart requests.
   */
  uploadImage: async (file: File): Promise<ImageUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<ImageUploadResponse>(
      "/uploads/imagen",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );
    return res.data;
  },

  /** Deletes an image from Cloudinary by its public ID. */
  deleteImage: async (publicId: string): Promise<void> => {
    await apiFetch(`/uploads/imagen/${encodeURIComponent(publicId)}`, {
      method: "DELETE",
    });
  },
};
