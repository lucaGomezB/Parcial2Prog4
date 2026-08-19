/**
 * ImageCarousel — Reusable image display component.
 *
 * Two variants:
 *   - "carousel" (default): single-image display with left/right arrows, counter.
 *     One delete button (X) positioned on the current image. Best for product
 *     cards and read-only views where screen real estate is limited.
 *   - "thumbs": static thumbnail grid, all images visible at once with
 *     individual delete buttons. Best for edit forms where the user needs
 *     to see and manage all images simultaneously.
 *
 * Props:
 *   - images: string[] — array of image URLs to display
 *   - publicIds: string[] — parallel array of Cloudinary public IDs
 *   - onDelete: (publicId: string) => void — delete callback
 *   - readOnly?: boolean — if true, hides delete buttons
 *   - variant?: "carousel" | "thumbs" — display mode (default: "carousel")
 *   - className?: string — appended to the outermost container
 */
import { useState, useEffect } from "react";

/** Applies Cloudinary optimization transformations to a raw image URL. */
function applyTransform(url: string | undefined): string {
  if (!url || !url.includes("cloudinary.com")) return url ?? "";
  return url.replace("/upload/", "/upload/f_auto,q_auto,c_fill/");
}

interface ImageCarouselProps {
  images: string[];
  publicIds: string[];
  onDelete: (publicId: string) => void;
  readOnly?: boolean;
  variant?: "carousel" | "thumbs";
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Delete-button atom (used by both variants)                        */
/* ------------------------------------------------------------------ */
function DeleteButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute top-1.5 right-1.5 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-700 cursor-pointer z-10 shadow"
      title="Eliminar imagen"
    >
      X
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Thumb variant — static grid of all images                         */
/* ------------------------------------------------------------------ */
function ThumbsView({
  images,
  publicIds,
  onDelete,
  readOnly,
  className,
}: ImageCarouselProps) {
  if (images.length === 0) {
    return (
      <div className={`w-full aspect-[4/3] bg-gray-300 flex items-center justify-center text-gray-500 rounded ${className}`}>
        Sin imagenes
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-3 gap-2 ${className}`}>
      {images.map((url, idx) => (
        <div
          key={idx}
          className="relative aspect-[4/3] bg-gray-100 rounded overflow-hidden group"
        >
          <img
            src={applyTransform(url)}
            alt={`Imagen ${idx + 1} de ${images.length}`}
            className="w-full h-full object-cover"
          />
          {!readOnly && (
            <DeleteButton
              onClick={() => {
                if (idx < publicIds.length && publicIds[idx]) {
                  onDelete(publicIds[idx]);
                }
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Carousel variant — classic single-image with arrows               */
/* ------------------------------------------------------------------ */
function CarouselView({
  images,
  publicIds,
  onDelete,
  readOnly,
  className,
}: ImageCarouselProps) {
  const [current, setCurrent] = useState(0);

  // Clamp current index when images array shrinks (e.g. after deletion).
  useEffect(() => {
    if (current >= images.length) {
      setCurrent(Math.max(0, images.length - 1));
    }
  }, [images, current]);

  if (images.length === 0) {
    return (
      <div className={`w-full aspect-[4/3] bg-gray-300 flex items-center justify-center text-gray-500 rounded ${className}`}>
        Sin imagenes
      </div>
    );
  }

  const hasMultiple = images.length > 1;

  const goLeft = () => {
    setCurrent((prev) => (prev === 0 ? images.length - 1 : prev - 1));
  };

  const goRight = () => {
    setCurrent((prev) => (prev === images.length - 1 ? 0 : prev + 1));
  };

  const handleDelete = () => {
    if (current >= publicIds.length) return;
    const targetId = publicIds[current];
    if (targetId) {
      onDelete(targetId);
    }
  };

  return (
    <div className={`relative w-full aspect-[4/3] bg-gray-100 rounded overflow-hidden group ${className}`}>
      <img
        src={applyTransform(images[current])}
        alt={`Imagen ${current + 1} de ${images.length}`}
        className="w-full h-full object-cover"
      />

      {!readOnly && <DeleteButton onClick={handleDelete} />}

      {hasMultiple && (
        <button
          type="button"
          onClick={goLeft}
          className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-black/70 cursor-pointer"
          title="Anterior"
        >
          {"\u2190"}
        </button>
      )}

      {hasMultiple && (
        <button
          type="button"
          onClick={goRight}
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-black/70 cursor-pointer"
          title="Siguiente"
        >
          {"\u2192"}
        </button>
      )}

      {hasMultiple && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/50 text-white text-xs px-2 py-0.5 rounded">
          {current + 1} / {images.length}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Public component — delegates to the selected variant              */
/* ------------------------------------------------------------------ */
export default function ImageCarousel(props: ImageCarouselProps) {
  const variant = props.variant ?? "carousel";

  if (variant === "thumbs") {
    return <ThumbsView {...props} />;
  }
  return <CarouselView {...props} />;
}
