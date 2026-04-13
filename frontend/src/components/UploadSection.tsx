"use client";

import React, { useState, useRef } from 'react';

interface UploadSectionProps {
  onUploadSuccess: (data: any) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export default function UploadSection({ onUploadSuccess, isLoading, setIsLoading }: UploadSectionProps) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFile = async (file: File) => {
    if (file.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }
    setError(null);
    setIsLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL 
        ? `${process.env.NEXT_PUBLIC_API_URL}/upload`
        : 'http://localhost:8000/upload';

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Processing failed");

      const result = await response.json();
      if (result.status === "success") {
        onUploadSuccess(result.data);
      } else {
        throw new Error(result.detail || "Unknown error");
      }
    } catch (err: any) {
      setError(err.message || "Failed to process the document.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-10">
      <div 
        className={`glass-panel p-10 flex flex-col items-center justify-center border-2 border-dashed transition-all duration-300 relative overflow-hidden group ${dragActive ? 'border-blue-500 bg-slate-800/80 shadow-[0_0_30px_rgba(59,130,246,0.3)]' : 'border-slate-600 hover:border-blue-400'}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        
        {isLoading ? (
          <div className="flex flex-col items-center animate-pulse">
            <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-6 shadow-[0_0_15px_rgba(59,130,246,0.5)]"></div>
            <p className="text-xl font-semibold text-slate-200">Analyzing Patient Record...</p>
            <p className="text-slate-400 mt-2 text-sm text-center">Extracting structured medical data from the case file...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center transform transition-transform duration-300 group-hover:scale-105 cursor-pointer">
            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-6 shadow-inner border border-slate-700 group-hover:bg-slate-700/80 group-hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] transition-all">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-10 h-10 text-blue-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-slate-100 mb-2">Upload Case File</h3>
            <p className="text-slate-400 text-center max-w-sm">Drag and drop your patient case PDF here, or click to browse files.</p>
            <p className="text-xs text-slate-500 mt-4 font-mono select-none">Supported: Handwritten, Typed PDFs</p>
          </div>
        )}
        <input 
          ref={fileInputRef}
          type="file" 
          className="hidden" 
          accept="application/pdf"
          onChange={handleChange}
        />
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center animate-bounce">
          {error}
        </div>
      )}
    </div>
  );
}
