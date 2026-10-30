"use strict";
(() => {
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const svg = document.getElementById("conversion-chart");
  const namespace = "http://www.w3.org/2000/svg";
  const points = data.example.original.flatMap((row, index) => {
    const result = data.example.converted[index];
    return row.generation_gwh === "" ? [] : [{
      name: `${row.country}, ${row.year}`,
      input: row.generation_gwh,
      output: result.generation_mwh,
    }];
  });
  points.push({name: "Synthetic reported-zero boundary", input: data.metrics.zero_gwh, output: data.metrics.zero_mwh});
  const maxInput = Math.max(...points.map(point => Number(point.input)));
  const maxOutput = Math.max(...points.map(point => Number(point.output)));
  const x = value => 105 + 730 * Number(value) / maxInput;
  const y = value => 325 - 270 * Number(value) / maxOutput;
  const node = (tag, attributes, text) => {
    const element = document.createElementNS(namespace, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text !== undefined) element.textContent = text;
    svg.appendChild(element);
    return element;
  };
  node("path", {d: "M105 45 V325 H855", fill: "none", stroke: "currentColor"});
  node("line", {x1: 105, x2: 855, y1: 325, y2: 325, class: "limit"});
  node("text", {x: 110, y: 385}, "Input generation (GWh)");
  node("text", {x: 105, y: 25}, "Returned generation (MWh)");
  node("text", {x: 835, y: 353, "text-anchor": "end", "data-metric": "alpha_gwh"}, data.metrics.alpha_gwh);
  node("text", {x: 94, y: 60, "text-anchor": "end", "data-metric": "alpha_mwh"}, data.metrics.alpha_mwh);
  node("text", {x: 95, y: 348, "text-anchor": "end", "data-metric": "zero_mwh"}, data.metrics.zero_mwh);
  node("text", {x: 510, y: 310}, "Dashed line: nonnegative measurement lower bound");
  const ordered = [...points].sort((left, right) => Number(left.input) - Number(right.input));
  node("path", {d: ordered.map((point, index) => `${index ? "L" : "M"}${x(point.input)} ${y(point.output)}`).join(" "), class: "series"});
  const selector = document.getElementById("chart-case");
  const readout = document.getElementById("chart-readout");
  const description = point => `Case: ${point.name}. Component: reported generation. Input: ${point.input} GWh. Demand: ${point.output} MWh. Lower limit: ${data.metrics.zero_mwh} MWh. The numerical boundary is met; physical operating limits are not evaluated.`;
  const inspect = index => {
    selector.value = String(index);
    readout.textContent = description(points[index]);
  };
  points.forEach((point, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = point.name;
    selector.appendChild(option);
    const circle = node("circle", {cx: x(point.input), cy: y(point.output), r: 6, tabindex: 0, class: "sample", "data-case": index, "aria-label": description(point)});
    const title = document.createElementNS(namespace, "title");
    title.textContent = description(point);
    circle.appendChild(title);
    circle.addEventListener("focus", () => inspect(index));
    circle.addEventListener("mouseenter", () => inspect(index));
    circle.addEventListener("click", () => inspect(index));
  });
  selector.addEventListener("change", () => inspect(Number(selector.value)));
  inspect(0);

  const sections = [...document.querySelectorAll("main > section")];
  const sectionSelector = document.getElementById("comment-section");
  sections.forEach(section => {
    const option = document.createElement("option");
    option.value = section.id;
    option.textContent = section.querySelector("h2").textContent;
    sectionSelector.appendChild(option);
  });
  const binding = document.querySelector('meta[name="document-binding"]').content;
  const status = document.getElementById("comment-status");
  const text = document.getElementById("comment-text");
  const list = document.getElementById("comment-list");
  let comments = [];
  const packet = () => ({document: "Energy mix module analysis", revision: "00", binding, comments});
  const serialize = () => JSON.stringify(packet(), null, 2) + "\n";
  const renderComments = () => {
    list.replaceChildren();
    comments.forEach(comment => {
      const item = document.createElement("li");
      item.className = "note";
      const title = sections.find(section => section.id === comment.section).querySelector("h2").textContent;
      item.textContent = `${title}: ${comment.text}`;
      list.appendChild(item);
    });
  };
  document.getElementById("add-comment").addEventListener("click", () => {
    if (!text.value.trim()) {
      status.textContent = "Enter a comment before adding it.";
      return;
    }
    comments.push({section: sectionSelector.value, text: text.value.trim()});
    text.value = "";
    renderComments();
    status.textContent = "The comment has been added to this page. Save or download comments before closing.";
  });
  document.getElementById("download-comments").addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([serialize()], {type: "application/json;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "energy-mix.comments.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = "Comments downloaded. Save the file beside the report.";
  });
  document.getElementById("save-comments").addEventListener("click", async () => {
    if (!window.showDirectoryPicker) {
      status.textContent = "Folder access is unavailable. Download comments and save them beside the report.";
      return;
    }
    try {
      const folder = await window.showDirectoryPicker({mode: "readwrite"});
      const file = await folder.getFileHandle("energy-mix.comments.json", {create: true});
      const stream = await file.createWritable();
      await stream.write(serialize());
      await stream.close();
      status.textContent = "Comments saved in the selected report folder.";
    } catch (error) {
      status.textContent = "Comments were not saved. Download comments or retry folder access.";
    }
  });
  document.getElementById("import-comments").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const saved = JSON.parse(await file.text());
      if (saved.document !== packet().document || saved.revision !== "00" || saved.binding !== binding || !Array.isArray(saved.comments)) {
        throw new Error("Document mismatch");
      }
      if (!saved.comments.every(comment => comment && sections.some(section => section.id === comment.section) && typeof comment.text === "string" && comment.text.trim())) {
        throw new Error("Invalid comment");
      }
      comments = [...comments, ...saved.comments];
      renderComments();
      status.textContent = "Saved comments opened for this document. Existing page comments are preserved.";
    } catch (error) {
      status.textContent = "Comments were not opened: the document binding or comment format does not match. Existing page comments are preserved.";
    }
  });
})();
