import { useRef } from "react";

export default function FileUpload({ onFileSelected, disabled = false }) {
  const inputRef = useRef(null);

  const chooseFile = () => {
    if (!disabled) inputRef.current?.click();
  };

  const onChange = (event) => {
    const file = event.target.files?.[0];
    if (file) onFileSelected(file);
    event.target.value = "";
  };

  return (
    <div className="upload-card">
      <div className="upload-copy">
        <span className="upload-icon">↑</span>
        <div>
          <strong>Upload dataset</strong>
          <p>CSV, TSV, JSON or Excel files</p>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.tsv,.tab,.json,.xlsx,.xls,text/csv,application/json"
        onChange={onChange}
        disabled={disabled}
        hidden
      />
      <button type="button" className="secondary-button" onClick={chooseFile} disabled={disabled}>
        Choose File
      </button>
    </div>
  );
}
