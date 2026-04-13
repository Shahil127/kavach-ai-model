import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider, SignInButton, Show, UserButton } from "@clerk/nextjs";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kavach AI | Discharge Summary",
  description: "AI-powered hospital discharge documentation platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ClerkProvider>
          <header className="absolute top-4 right-4 z-[100]">
            <Show when="signed-in">
              <UserButton />
            </Show>
          </header>
          <Show when="signed-out">
            <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-slate-900">
               <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />
               <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
               <div className="z-10 text-center mb-8">
                  <div className="w-16 h-16 mx-auto bg-gradient-to-tr from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-500/30 mb-6">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-10 h-10 text-white">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                    </svg>
                  </div>
                  <h1 className="text-4xl font-extrabold text-white mb-2 tracking-tight">Kavach IPD</h1>
                  <p className="text-slate-400">Restricted Medical Portal</p>
               </div>
               <div className="z-10 bg-white/5 border border-white/10 p-8 rounded-2xl backdrop-blur-md max-w-sm w-full text-center shadow-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">Authorized Personnel Only</h2>
                  <p className="text-slate-300 text-sm mb-8 leading-relaxed">
                     This system is restricted to administrators. Contact Kavach AI for an authorized account.
                  </p>
                  <div className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-lg transition-all shadow-lg hover:shadow-blue-500/50 flex justify-center cursor-pointer">
                    <SignInButton mode="modal">Sign In Securely</SignInButton>
                  </div>
               </div>
            </div>
          </Show>
          <Show when="signed-in">
             {children}
          </Show>
        </ClerkProvider>
      </body>
    </html>
  );
}
