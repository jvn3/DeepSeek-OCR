/**
 * Next.js Integration Example for DeepSeek-OCR API
 * 
 * This shows how to integrate the OCR API with your Next.js + Supabase app
 */

import { createClient } from '@supabase/supabase-js';
import { useState } from 'react';

// Initialize Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const OCR_API_URL = process.env.NEXT_PUBLIC_OCR_API_URL || 'http://localhost:8000';

interface OCRResult {
  pageIndex: number;
  text: string;
  blocks?: any[];
  lines?: any[];
  words?: any[];
  language?: string;
  timeMs: number;
}

export function useOCR() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Perform OCR on an image file
   */
  const ocrImage = async (
    imageFile: File,
    options: {
      docType?: string;
      returnLayout?: boolean;
      returnWords?: boolean;
    } = {}
  ): Promise<OCRResult | null> => {
    setLoading(true);
    setError(null);

    try {
      // Get the current user's session
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('Not authenticated');
      }

      // Create form data
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('doc_type', options.docType || 'auto');
      formData.append('return_layout', String(options.returnLayout ?? true));
      formData.append('return_words', String(options.returnWords ?? true));

      // Call OCR API with Supabase JWT token
      const response = await fetch(`${OCR_API_URL}/v1/ocr/image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'OCR failed');
      }

      const result: OCRResult = await response.json();
      return result;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('OCR error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Extract entities and fields from OCR text
   */
  const parseSemanticContent = async (
    text: string,
    layout?: any,
    hints?: Record<string, string>
  ) => {
    setLoading(true);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${OCR_API_URL}/v1/parse/semantic`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          doc_type: 'auto',
          text,
          layout,
          hints,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Semantic parsing failed');
      }

      return await response.json();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Semantic parse error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Match extracted fields to a form schema
   */
  const matchToForm = async (
    formId: string,
    fields: Record<string, any>,
    strict: boolean = false
  ) => {
    setLoading(true);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${OCR_API_URL}/v1/forms/match`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          form_id: formId,
          fields,
          strict,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Form matching failed');
      }

      return await response.json();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Form match error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    ocrImage,
    parseSemanticContent,
    matchToForm,
    loading,
    error,
  };
}

/**
 * Example Component
 */
export function OCRUploader() {
  const { ocrImage, parseSemanticContent, matchToForm, loading, error } = useOCR();
  const [result, setResult] = useState<any>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Step 1: OCR the image
    const ocrResult = await ocrImage(file, {
      docType: 'passport',
      returnLayout: true,
      returnWords: true,
    });

    if (!ocrResult) return;

    console.log('OCR Result:', ocrResult);

    // Step 2: Extract entities and fields
    const semantic = await parseSemanticContent(
      ocrResult.text,
      {
        blocks: ocrResult.blocks,
        lines: ocrResult.lines,
        words: ocrResult.words,
      },
      { country: 'US', dateFormat: 'MDY' }
    );

    if (!semantic) return;

    console.log('Entities:', semantic.entities);
    console.log('Fields:', semantic.fields);

    // Step 3: Match to form (e.g., DS-160)
    const formMatch = await matchToForm('ds-160@v2025-10', semantic.fields);

    if (!formMatch) return;

    console.log('Form Mapping:', formMatch.mapping);

    // Step 4: Save to Supabase (with encryption if needed)
    await supabase.from('documents').insert({
      ocr_text: ocrResult.text,
      entities: semantic.entities,
      fields: semantic.fields,
      form_mapping: formMatch.mapping,
      created_at: new Date().toISOString(),
    });

    setResult({
      ocr: ocrResult,
      semantic,
      formMatch,
    });
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">OCR Document Upload</h2>
      
      <input
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        disabled={loading}
        className="mb-4"
      />

      {loading && <p className="text-blue-600">Processing...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}

      {result && (
        <div className="mt-4 space-y-4">
          <div>
            <h3 className="font-semibold">Extracted Text:</h3>
            <pre className="bg-gray-100 p-2 rounded">
              {result.ocr.text.substring(0, 500)}...
            </pre>
          </div>

          <div>
            <h3 className="font-semibold">Entities Found:</h3>
            <ul className="list-disc pl-5">
              {result.semantic.entities.map((entity: any, i: number) => (
                <li key={i}>
                  {entity.label}: {entity.text} ({(entity.conf * 100).toFixed(1)}%)
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold">Form Mappings:</h3>
            <ul className="list-disc pl-5">
              {result.formMatch.mapping.map((m: any, i: number) => (
                <li key={i}>
                  {m.form_field} ← {m.source_field} ({(m.confidence * 100).toFixed(1)}%)
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
