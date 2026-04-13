"use client";

import React, { useState } from 'react';
import UploadSection from '@/components/UploadSection';
import DataReviewEditor from '@/components/DataReviewEditor';

export default function Home() {
  const [extractedData, setExtractedData] = useState<Record<string, any> | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleReset = () => {
    setExtractedData(null);
  };

  return (
    <main className="min-h-screen relative overflow-hidden flex flex-col items-center">
      {/* Background Decorators */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-5xl mx-auto px-4 py-16 flex-1 flex flex-col relative z-10">
        <header className="text-center mb-12 animate-[float_4s_ease-in-out_infinite]">
          <div className="inline-flex items-center justify-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-tr from-blue-500 to-purple-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-8 h-8 text-white">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 drop-shadow-sm">
              AI Discharge Summary
            </h1>
          </div>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto">
            Upload patient case files and instantly generate beautifully formatted discharge summaries automatically.
          </p>
        </header>

        <section className="flex-1 flex flex-col justify-center items-center w-full">
          {!extractedData ? (
            <UploadSection 
              onUploadSuccess={setExtractedData} 
              isLoading={isLoading} 
              setIsLoading={setIsLoading} 
            />
          ) : (
            <DataReviewEditor 
              initialData={extractedData} 
              onReset={handleReset} 
            />
          )}
        </section>
      </div>

    </main>
  );
}
