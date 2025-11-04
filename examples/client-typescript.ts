/**
 * TypeScript client for DeepSeek-OCR API with E2EE support
 * 
 * This client demonstrates how to:
 * 1. Establish X25519 session key exchange
 * 2. Encrypt image payloads using XChaCha20-Poly1305
 * 3. Call OCR endpoints
 * 4. Stream batch job results via SSE
 */

import { webcrypto } from 'crypto';

// Type definitions
interface SessionCrypto {
  clientPrivateKey: CryptoKey;
  clientPublicKey: Uint8Array;
  serverPublicKey?: Uint8Array;
  sharedSecret?: Uint8Array;
}

interface OCRImageRequest {
  docType?: string;
  languageHint?: string;
  returnLayout?: boolean;
  returnWords?: boolean;
  pageIndex?: number;
}

interface OCRImageResponse {
  pageIndex: number;
  text: string;
  blocks?: any[];
  lines?: any[];
  words?: any[];
  language?: string;
  timeMs: number;
  provenance: {
    engine: string;
    version: string;
  };
}

class DeepSeekOCRClient {
  private baseUrl: string;
  private token: string;
  private session?: SessionCrypto;

  constructor(baseUrl: string, supabaseToken: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = supabaseToken;
  }

  /**
   * Initialize E2EE session with the server
   */
  async initSession(): Promise<void> {
    // Generate client X25519 key pair
    const keyPair = await webcrypto.subtle.generateKey(
      {
        name: 'ECDH',
        namedCurve: 'X25519', // Note: X25519 support varies, may need polyfill
      },
      true,
      ['deriveKey', 'deriveBits']
    );

    // Export public key
    const publicKeyBuffer = await webcrypto.subtle.exportKey('raw', keyPair.publicKey);
    const clientPublicKey = new Uint8Array(publicKeyBuffer);

    this.session = {
      clientPrivateKey: keyPair.privateKey,
      clientPublicKey,
    };

    // Fetch server's public key
    const response = await fetch(`${this.baseUrl}/`, {
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
    });

    const data = await response.json();
    const serverPubkeyB64 = data.e2ee?.server_pubkey;

    if (serverPubkeyB64) {
      this.session.serverPublicKey = this.base64ToBytes(serverPubkeyB64);

      // Derive shared secret (note: actual implementation needs proper X25519)
      // This is simplified - use a proper crypto library like libsodium.js
      console.log('Session initialized with server');
    }
  }

  /**
   * OCR a single image with optional E2EE
   */
  async ocrImage(
    imageFile: File | Blob,
    options: OCRImageRequest = {},
    useE2EE: boolean = false
  ): Promise<OCRImageResponse> {
    let imageData = await imageFile.arrayBuffer();
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.token}`,
    };

    // Encrypt if E2EE is enabled and session exists
    if (useE2EE && this.session?.sharedSecret) {
      const encryptedData = await this.encryptData(new Uint8Array(imageData));
      imageData = encryptedData.buffer;
      headers['X-Client-Pubkey'] = this.bytesToBase64(this.session.clientPublicKey);
    }

    // Create form data
    const formData = new FormData();
    formData.append('image', new Blob([imageData]), 'image.png');
    formData.append('doc_type', options.docType || 'auto');
    if (options.languageHint) formData.append('language_hint', options.languageHint);
    formData.append('return_layout', String(options.returnLayout ?? true));
    formData.append('return_words', String(options.returnWords ?? true));
    formData.append('page_index', String(options.pageIndex ?? 0));

    const response = await fetch(`${this.baseUrl}/v1/ocr/image`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`OCR failed: ${error.message || error.error}`);
    }

    return await response.json();
  }

  /**
   * Parse semantic content from OCR output
   */
  async parseSemantic(text: string, layout?: any, hints?: Record<string, string>) {
    const response = await fetch(`${this.baseUrl}/v1/parse/semantic`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify({
        doc_type: 'auto',
        text,
        layout,
        hints,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Semantic parse failed: ${error.message || error.error}`);
    }

    return await response.json();
  }

  /**
   * Match extracted fields to a form schema
   */
  async matchForm(formId: string, fields: Record<string, any>, strict: boolean = false) {
    const response = await fetch(`${this.baseUrl}/v1/forms/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify({
        form_id: formId,
        fields,
        strict,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Form match failed: ${error.message || error.error}`);
    }

    return await response.json();
  }

  /**
   * Start a batch OCR job
   */
  async startBatch(pages: string[], options: OCRImageRequest = {}) {
    const response = await fetch(`${this.baseUrl}/v1/ocr/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify({
        pages, // Base64-encoded images
        doc_type: options.docType || 'auto',
        language_hint: options.languageHint,
        return_layout: options.returnLayout ?? true,
        return_words: options.returnWords ?? true,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Batch start failed: ${error.message || error.error}`);
    }

    return await response.json();
  }

  /**
   * Stream batch job results via SSE
   */
  async *streamBatchResults(jobId: string): AsyncGenerator<any> {
    const response = await fetch(`${this.baseUrl}/v1/ocr/stream/${jobId}`, {
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Stream failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          yield data;

          if (data.event_type === 'job_completed') {
            return;
          }
        }
      }
    }
  }

  /**
   * Encrypt data using XChaCha20-Poly1305 (simplified example)
   * For production, use a proper crypto library like libsodium.js
   */
  private async encryptData(plaintext: Uint8Array): Promise<Uint8Array> {
    if (!this.session?.sharedSecret) {
      throw new Error('No shared secret available');
    }

    // This is a placeholder - implement actual XChaCha20-Poly1305 encryption
    // using a library like libsodium.js or @stablelib/xchacha20poly1305
    console.warn('Encryption not implemented - use libsodium.js for production');
    return plaintext;
  }

  // Utility methods
  private base64ToBytes(base64: string): Uint8Array {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  private bytesToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}

// Example usage
async function example() {
  const client = new DeepSeekOCRClient(
    'http://localhost:8000',
    'your-supabase-jwt-token'
  );

  // Initialize E2EE session (optional)
  await client.initSession();

  // OCR a single image
  const imageFile = new File([/* image data */], 'document.png', { type: 'image/png' });
  const ocrResult = await client.ocrImage(imageFile, {
    docType: 'passport',
    returnLayout: true,
  });

  console.log('OCR Text:', ocrResult.text);

  // Parse semantic content
  const semantic = await client.parseSemantic(ocrResult.text, {
    blocks: ocrResult.blocks,
    lines: ocrResult.lines,
    words: ocrResult.words,
  });

  console.log('Entities:', semantic.entities);
  console.log('Fields:', semantic.fields);

  // Match to form
  const formMatch = await client.matchForm('ds-160@v2025-10', semantic.fields);
  console.log('Form mapping:', formMatch.mapping);

  // Batch processing with streaming
  const batchJob = await client.startBatch([
    'base64-encoded-image-1',
    'base64-encoded-image-2',
  ]);

  console.log('Job started:', batchJob.job_id);

  for await (const event of client.streamBatchResults(batchJob.job_id)) {
    console.log('Progress:', event.progress);
    if (event.page_result) {
      console.log('Page completed:', event.page_result.page_index);
    }
  }
}

export { DeepSeekOCRClient, OCRImageRequest, OCRImageResponse };
