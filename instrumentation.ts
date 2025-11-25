// instrumentation.ts - Loads before everything else in Next.js
// Polyfill for Next.js 15 File global issue with undici

export async function register() {
  if (typeof globalThis.File === 'undefined') {
    globalThis.File = class File extends Blob {
      name: string;
      lastModified: number;
      
      constructor(parts: BlobPart[], name: string, options?: FilePropertyBag) {
        super(parts, options);
        this.name = name;
        this.lastModified = options?.lastModified ?? Date.now();
      }
    } as any;
  }
}
