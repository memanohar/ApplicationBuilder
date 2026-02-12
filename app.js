// =====================
// DOM ELEMENTS
// =====================
document.addEventListener('DOMContentLoaded', () => {

  const generateBtn = document.getElementById('generateBtn');
  const outputPanel = document.getElementById('outputPanel');
  const projectNameInput = document.getElementById('projectName');
  const projectTypeSelect = document.getElementById('projectType');
  const descriptionTextarea = document.getElementById('description');
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');
  const downloadBtn = document.getElementById('downloadBtn');
  const themeToggle = document.getElementById('themeToggle');
  const deployBtn = document.getElementById('deployBtn');
  const addFeatureBtn = document.getElementById('addFeatureBtn');
  const previewFrame = document.getElementById('preview-frame');

  const API_URL = 'http://localhost:5000';
   let lastGeneratedProjectName = null;

  // Restore last project from previous session
  const savedProject = localStorage.getItem('lastProjectName');
  if (savedProject) {
    lastGeneratedProjectName = savedProject;
  }

  // =====================
  // THEME TOGGLE
  // =====================
  (function setupThemeToggle() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    let currentTheme = localStorage.getItem('theme') || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', currentTheme);

    if (themeToggle) {
      themeToggle.textContent = currentTheme === 'dark' ? '🌞' : '🌗';
      themeToggle.onclick = () => {
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        themeToggle.textContent = currentTheme === 'dark' ? '🌞' : '🌗';
      };
    }
  })();

  // =====================
  // TAB SWITCHING
  // =====================
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.dataset.tab;
      tabButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      button.classList.add('active');
      document.getElementById(`${tabName}-tab`)?.classList.add('active');
    });
  });

  // =====================
  // GENERATE WEBSITE
  // =====================
  async function generateProject() {
    const projectName = projectNameInput.value || 'My Website';
    const projectType = projectTypeSelect.value;
    const description = descriptionTextarea.value;

    if (!description.trim()) {
      alert('Please describe your project in detail!');
      return;
    }

    const techStack = Array.from(
      document.querySelectorAll('.tech-stack input:checked')
    ).map(cb => cb.value);

    generateBtn.disabled = true;
    generateBtn.querySelector('.button-text').style.display = 'none';
    generateBtn.querySelector('.button-loader').style.display = 'inline-flex';

    previewFrame.srcdoc = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888">
      Generating your website...
    </div>`;

    try {
      const res = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectName, projectType, description, techStack })
      });

      if (!res.ok) throw new Error(`Backend error ${res.status}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      updateCodePanels(data.code);
      previewFrame.srcdoc = data.code.html;
      outputPanel.style.display = 'block';
      outputPanel.scrollIntoView({ behavior: 'smooth' });

      lastGeneratedProjectName = projectName;
      localStorage.setItem('lastProjectName', projectName);
      notify('✅ Website generated successfully', 'success');

    } catch (err) {
      console.error(err);
      notify('⚠️ Backend error. Showing template.', 'error');
      loadTemplateCode();
    } finally {
      generateBtn.disabled = false;
      generateBtn.querySelector('.button-text').style.display = 'inline';
      generateBtn.querySelector('.button-loader').style.display = 'none';
    }
  }

  if (generateBtn) {
    generateBtn.addEventListener('click', (e) => {
      e.preventDefault();
      generateProject();
    });
  }
  // =====================
  // ADD FEATURE DYNAMICALLY
  // =====================
  if (addFeatureBtn) {
    addFeatureBtn.addEventListener('click', async () => {
      if (!lastGeneratedProjectName) {
        alert("Generate a project first!");
        return;
      }
      const featureDescription = prompt("Describe the feature to add (e.g., 'Add contact form with email validation'):");
      if (!featureDescription || !featureDescription.trim()) return;

      addFeatureBtn.disabled = true;
      addFeatureBtn.textContent = "➕ Adding...";

      try {
        const res = await fetch(`${API_URL}/api/add-feature`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectName: lastGeneratedProjectName, featureDescription })
        });
        if (!res.ok) throw new Error(`Backend error ${res.status}`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        // Update preview & code without resetting UI
        updateCodePanels(data.code);
        previewFrame.srcdoc = data.code.html;

        notify('✨ Feature added successfully!', 'success');
      } catch (err) {
        console.error(err);
        notify('⚠️ Failed to add feature', 'error');
      } finally {
        addFeatureBtn.disabled = false;
        addFeatureBtn.textContent = "➕ Add Feature";
      }
    });
  }

  // =====================
  // CODE & PREVIEW UTILITIES
  // =====================
  function updateCodePanels(code) {
    setHighlighted('html', code.html, 'html');
    setHighlighted('css', code.css, 'css');
    setHighlighted('js', code.js, 'javascript');
    setHighlighted('backend', code.backend, 'python');
  }

  function setHighlighted(lang, code, prismLang) {
    document.getElementById(`${lang}-code`).innerHTML =
      Prism.highlight(code || '', Prism.languages[prismLang], prismLang);
  }

  function notify(msg, type = 'info') {
    const n = document.createElement('div');
    n.textContent = msg;
    n.style.cssText = `
      position:fixed;top:20px;right:20px;
      background:${type === 'success' ? '#10b981' : '#ef4444'};
      color:white;padding:14px 20px;border-radius:8px;z-index:9999
    `;
    document.body.appendChild(n);
    setTimeout(() => n.remove(), 4000);
  }

  function loadTemplateCode() {
    const html = `<html><body style="font-family:sans-serif">
      <h1>Template Loaded</h1>
      <p>Backend not available.</p>
    </body></html>`;
    updateCodePanels({ html, css: '', js: '', backend: '' });
    previewFrame.srcdoc = html;
    outputPanel.style.display = 'block';
  }

  // =====================
  // DOWNLOAD PROJECT AS ZIP
  // =====================
  // downloadBtn.addEventListener('click', async () => {
  //   if (!lastGeneratedProjectName) return;
  //   try {
  //     const res = await fetch(`${API_URL}/api/generate`, {
  //       method: 'POST',
  //       headers: { 'Content-Type': 'application/json' },
  //       body: JSON.stringify({ projectName: lastGeneratedProjectName })
  //     });
  //     const data = await res.json();
  //     const zip = new JSZip();
  //     zip.file("index.html", data.code.html);
  //     zip.file("style.css", data.code.css);
  //     zip.file("app.js", data.code.js);
  //     zip.file("backend.py", data.code.backend);
  //     zip.generateAsync({ type: "blob" }).then(blob => {
  //       saveAs(blob, `${lastGeneratedProjectName}.zip`);
  //     });
  //   } catch (err) {
  //     console.error(err);
  //     notify('⚠️ Failed to download project', 'error');
  //   }
  // });
  if (downloadBtn) {
downloadBtn.addEventListener('click', async () => {
  if (!lastGeneratedProjectName) {
    notify('⚠️ Generate a project before downloading.', 'error');
    return;
  }

  try {
    const res = await fetch(`${API_URL}/api/projects/${encodeURIComponent(lastGeneratedProjectName)}`);
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to load project');
    }

    const { html, css, js, backend } = data.code;
    const zip = new JSZip();
    zip.file("index.html", html);
    zip.file("style.css", css);
    zip.file("app.js", js);
    zip.file("backend.py", backend);

    const blob = await zip.generateAsync({ type: "blob" });
    saveAs(blob, `${lastGeneratedProjectName}.zip`);
    notify('📥 Project ZIP downloaded.', 'success');
  } catch (err) {
    console.error(err);
    notify('⚠️ Failed to download project', 'error');
  }
}
);}

// =====================
// DEPLOY (COPY TO deploy_target ONLY)
// =====================
if (deployBtn) {
deployBtn.addEventListener('click', async () => {
  if (!lastGeneratedProjectName) {
    alert("Generate a project first before deploying!");
    return;
  }

  if (!confirm(`Copy "${lastGeneratedProjectName}" into deploy_target?`)) {
    return;
  }

  const originalText = deployBtn.textContent;
  deployBtn.disabled = true;
  deployBtn.textContent = "📦 Copying...";

  try {
    const res = await fetch(`${API_URL}/api/deploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectName: lastGeneratedProjectName })
    });

    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.error || `Deploy failed with status ${res.status}`);
    }

    notify(`✅ Copied to deploy_target: ${lastGeneratedProjectName}`, 'success');
  } catch (err) {
    console.error(err);
    notify(`⚠️ Failed to copy project: ${err.message}`, 'error');
  } finally {
    deployBtn.disabled = false;
    deployBtn.textContent = originalText;
  }
});}
});