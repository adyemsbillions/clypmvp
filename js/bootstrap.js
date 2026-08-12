(() => {
  const KEY = 'clyp:projects:v2';
  const parse = value => { try { return JSON.parse(value); } catch { return null; } };
  const read = () => {
    const value = parse(localStorage.getItem(KEY));
    return Array.isArray(value) ? value : [];
  };
  const write = projects => localStorage.setItem(KEY, JSON.stringify(projects));
  const newId = () => (crypto?.randomUUID ? crypto.randomUUID() : `clyp-${Date.now()}-${Math.random().toString(36).slice(2,9)}`);
  const clone = value => JSON.parse(JSON.stringify(value));

  window.ClypStore = {
    list() {
      return read().sort((a,b) => String(b.updated_at).localeCompare(String(a.updated_at)));
    },
    get(id) {
      const project = read().find(item => String(item.id) === String(id));
      return project ? clone(project) : null;
    },
    save(design) {
      const projects = read();
      const now = new Date().toISOString();
      const saved = clone(design);
      saved.id = saved.id || newId();
      saved.updated_at = now;
      saved.created_at = saved.created_at || now;
      const index = projects.findIndex(item => String(item.id) === String(saved.id));
      if (index >= 0) projects[index] = saved; else projects.unshift(saved);
      write(projects.slice(0,60));
      return clone(saved);
    },
    remove(id) {
      write(read().filter(item => String(item.id) !== String(id)));
    },
    clear() { localStorage.removeItem(KEY); }
  };
})();
