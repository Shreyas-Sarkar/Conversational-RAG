type AppShellProps = {
  sidebar: React.ReactNode;
  main: React.ReactNode;
  inspector: React.ReactNode;
};

export function AppShell({ sidebar, main, inspector }: AppShellProps) {
  return (
    <div className="grid min-h-screen grid-cols-1 gap-4 p-4 lg:grid-cols-[20%_60%_20%]">
      <aside className="rounded-[18px] border-4 border-black bg-sky p-4 shadow-brutal">{sidebar}</aside>
      <main className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">{main}</main>
      <aside className="rounded-[18px] border-4 border-black bg-moss p-4 shadow-brutal">{inspector}</aside>
    </div>
  );
}
