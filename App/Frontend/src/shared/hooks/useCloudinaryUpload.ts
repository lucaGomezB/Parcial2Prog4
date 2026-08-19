/**
 * useCloudinaryUpload — Hook for Cloudinary Upload Widget lifecycle.
 *
 * Encapsulates the Cloudinary CDN script loading (singleton), widget
 * creation, and image deletion. Supports single and multiple upload modes.
 *
 * Usage:
 *   const { abrirWidget, eliminarImagen, uploadingImages } = useCloudinaryUpload("multiple");
 *
 *   // In a button onClick:
 *   abrirWidget((secureUrl, publicId) => {
 *     // Add URL to form state and track publicId
 *   });
 *
 *   // To delete an uploaded image:
 *   await eliminarImagen(publicId);
 *
 * @param mode - "single" for single-file upload, "multiple" for multi-file (default: "single").
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { uploadsApi } from "@/shared/api/uploads";
import { addToast } from "@/shared/components/Toast";

const SCRIPT_ID = "cloudinary-upload-widget";
const CLOUD_NAME = "dqp5n999t";
const UPLOAD_PRESET = "fs_default";

/** Module-level flag ensures the CDN script is injected exactly once. */
let scriptLoadStarted = false;

export function useCloudinaryUpload(mode: "single" | "multiple" = "single") {
  const widgetRef = useRef<{ open: () => void } | null>(null);
  const [uploadingImages, setUploadingImages] = useState(false);

  // Load Cloudinary CDN script once per application lifetime
  useEffect(() => {
    if (scriptLoadStarted) return;
    if (document.getElementById(SCRIPT_ID)) {
      scriptLoadStarted = true;
      return;
    }
    scriptLoadStarted = true;
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = "https://upload-widget.cloudinary.com/global/all.js";
    script.async = true;
    document.body.appendChild(script);
  }, []);

  /**
   * Opens the Cloudinary upload widget.
   *
   * @param onSuccess - Called once per successfully uploaded image with
   *   the secure URL and public ID.
   */
  const abrirWidget = useCallback(
    (onSuccess: (secureUrl: string, publicId: string) => void) => {
      const cloudinary = (window as unknown as Record<string, unknown>).cloudinary as
        | { createUploadWidget: Function }
        | undefined;

      if (!cloudinary || typeof cloudinary.createUploadWidget !== "function") {
        addToast("error", "El widget de Cloudinary no se ha cargado. Recargue la pagina.");
        return;
      }

      const widget = cloudinary.createUploadWidget(
        {
          cloudName: CLOUD_NAME,
          uploadPreset: UPLOAD_PRESET,
          multiple: mode === "multiple",
          maxFiles: mode === "multiple" ? 10 : 1,
        },
        (error: unknown, result: { event: string; info?: { secure_url: string; public_id: string } }) => {
          if (error) {
            addToast("error", "Error al subir imagen a Cloudinary");
            return;
          }
          if (result?.event === "success" && result.info) {
            onSuccess(result.info.secure_url, result.info.public_id);
          }
        }
      );

      widgetRef.current = widget;
      widget.open();
    },
    [mode]
  );

  /**
   * Deletes an uploaded image from Cloudinary by its public ID.
   * Manages the uploadingImages state and shows toast on error.
   */
  const eliminarImagen = useCallback(async (publicId: string): Promise<void> => {
    if (!confirm("Eliminar esta imagen?")) return;
    setUploadingImages(true);
    try {
      await uploadsApi.deleteImage(publicId);
      addToast("exito", "Imagen eliminada correctamente");
    } catch (err: unknown) {
      // Extract backend detail message if available (Axios error shape)
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      addToast("error", detail ?? "Error al eliminar la imagen");
    } finally {
      setUploadingImages(false);
    }
  }, []);

  return { abrirWidget, eliminarImagen, uploadingImages };
}
