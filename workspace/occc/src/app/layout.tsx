import "./globals.css";
import "react-toastify/dist/ReactToastify.css";
import { ThemeProvider } from "@/context/ThemeContext";
import { ProjectProvider } from "@/context/ProjectContext";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { ToastContainer } from "react-toastify";
import BackgroundSyncTrigger from "@/components/sync/BackgroundSyncTrigger";

export const metadata = {
  title: "OCCC - OpenClaw Control Center",
  description: "Development workflow control center",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        <ThemeProvider>
          <BackgroundSyncTrigger />
          <ProjectProvider>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              <div className="flex flex-col flex-1 overflow-hidden">
                <Header />
                <main className="flex-1 overflow-auto p-6">
                  {children}
                </main>
              </div>
            </div>
          </ProjectProvider>
          <ToastContainer position="bottom-right" autoClose={3000} theme="colored" />
        </ThemeProvider>
      </body>
    </html>
  );
}
