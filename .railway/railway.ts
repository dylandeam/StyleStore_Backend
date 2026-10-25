import { defineRailway, github, project, service } from "railway/iac";
// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "StyleStore_Backend";
export default defineRailway(() => {
  const StyleStore_Backend = service("StyleStore_Backend", {
    source: github("dylandeam/StyleStore_Backend", { branch: "main", checkSuites: false }),
    build: { buildEnvironment: "V3", builder: "NIXPACKS" },
    start: "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}",
    replicas: { "iad": 1 },
    networking: { privateNetworkEndpoint: "web" },
  });

  return project("accomplished-mindfulness", {
    variables: { managed: false },
    resources: [StyleStore_Backend],
  });
});
