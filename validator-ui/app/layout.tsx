export const metadata = {
  title: "Transcript Validator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif",
          backgroundColor: "#0f172a",
          color: "#e5e7eb",
        }}
      >
        <div
          style={{
            maxWidth: 900,
            margin: "0 auto",
            padding: "24px 16px 32px",
          }}
        >
          <h1
            style={{
              fontSize: 24,
              marginBottom: 16,
              fontWeight: 600,
            }}
          >
            Transcript Validator
          </h1>
          {children}
        </div>
      </body>
    </html>
  );
}

