"use client";

import React, { useRef, useState, useEffect } from 'react';

// Next.js dynamic import for html2pdf (since it uses window, it fails in SSR)
const html2pdf = typeof window !== "undefined" ? require("html2pdf.js") : null;

interface DataReviewEditorProps {
  initialData: Record<string, any>;
  onReset: () => void;
}

export default function DataReviewEditor({ initialData, onReset }: DataReviewEditorProps) {
  const documentRef = useRef<HTMLDivElement>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const [data, setData] = useState({
    patient_details: initialData?.patient_details || {},
    diagnosis: initialData?.diagnosis || { primary: [], associated_conditions: [] },
    presenting_complaints: initialData?.presenting_complaints || [],
    past_history: initialData?.past_history || [],
    allergies: initialData?.allergies || { known: false, details: "" },
    clinical_exam: initialData?.clinical_exam || { vitals: {}, general: {}, systemic: {} },
    investigations: initialData?.investigations || [],
    procedures: initialData?.procedures || "",
    hospital_course: initialData?.hospital_course || "",
    condition_at_discharge: initialData?.condition_at_discharge || {},
    medications: initialData?.medications || [],
    nutrition: initialData?.nutrition || [],
    rehabilitation: initialData?.rehabilitation || "",
    follow_up: initialData?.follow_up || {}
  });

  const handleDownloadPDF = async () => {
    if (!documentRef.current || !html2pdf) return;
    setIsGeneratingPdf(true);
    try {
      const element = documentRef.current;
      const opt = {
        margin:       0.5,
        filename:     'discharge_summary.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, letterRendering: true },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
      };
      
      await html2pdf().set(opt).from(element).save();
    } catch (err) {
      console.error(err);
      alert("Failed to generate PDF.");
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const handleDownloadWord = () => {
    if (!documentRef.current) return;
    const html = documentRef.current.innerHTML;
    
    const header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' " +
                   "xmlns:w='urn:schemas-microsoft-com:office:word' " +
                   "xmlns='http://www.w3.org/TR/REC-html40'>" +
                   "<head><meta charset='utf-8'><title>Discharge Summary</title></head><body>";
    const footer = "</body></html>";
    const sourceHTML = header + html + footer;

    const blob = new Blob(['\ufeff', sourceHTML], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const downloadLink = document.createElement("a");
    downloadLink.href = url;
    downloadLink.download = "discharge_summary.doc";
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    
    document.body.removeChild(downloadLink);
    URL.revokeObjectURL(url);
  };

  const footerData = {
      hospitalName: "B M Birla Heart Hospital",
      hospitalAddress: "1/1 National Library Avenue, Kolkata - 700 027, India",
      hospitalPhone: "+91 33 4088 4088",
      doctorName: data.follow_up?.recommended_doctor || "________________________",
      doctorTitle: "Consultant"
  };

  const Checkbox = ({ value, onChange, label }: { value: boolean, onChange: (val: boolean) => void, label?: string }) => {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", marginRight: "10px" }}>
        <span
          onClick={() => onChange(!value)}
          onMouseDown={(e) => e.preventDefault()}
          style={{ cursor: "pointer", fontWeight: "bold", fontSize: "14pt", userSelect: "none" }}
        >
          {value ? "☑" : "☐"}
        </span>
        {label && <span>{label}</span>}
      </span>
    );
  };

  return (
    <div className="w-full flex flex-col items-center mt-6 animate-[float_0.5s_ease-out_forwards]">
       <div className="flex flex-wrap justify-center gap-4 mb-6 z-20 w-full px-4">
          <button 
             onClick={onReset} 
             className="px-6 py-3 bg-slate-800 text-slate-200 rounded-lg hover:bg-slate-700 transition-colors border border-slate-600 shadow-md font-medium"
          >
             Upload Another
          </button>
          <div className="flex gap-4 ml-auto">
             <button 
               onClick={handleDownloadPDF} 
               disabled={isGeneratingPdf}
               className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 font-bold text-white rounded-lg shadow-[0_0_15px_rgba(37,99,235,0.4)] hover:shadow-[0_0_25px_rgba(37,99,235,0.6)] hover:-translate-y-0.5 transition-all flex items-center"
             >
               {isGeneratingPdf ? "Exporting..." : "Download PDF"}
             </button>
             <button 
               onClick={handleDownloadWord} 
               className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 font-bold text-white rounded-lg shadow-[0_0_15px_rgba(79,70,229,0.4)] hover:shadow-[0_0_25px_rgba(79,70,229,0.6)] hover:-translate-y-0.5 transition-all flex items-center"
             >
               Download Word
             </button>
          </div>
       </div>

       {isClient && (
       <div className="w-full max-w-[850px] mx-auto overflow-x-auto pb-10">
         <div 
           className="bg-white mx-auto shadow-2xl relative"
           style={{ 
               width: '8.5in',
               minHeight: '11in',
               margin: "0 auto",
               borderRadius: "4px"
           }}
         >
           <div 
             ref={documentRef} 
             contentEditable={true} 
             suppressContentEditableWarning={true}
             className="w-full h-full text-black outline-none focus:ring-4 ring-blue-500/30 transition-shadow"
             style={{ 
                 padding: '0.8in 0.8in', 
                 fontFamily: 'Arial, Helvetica, sans-serif', 
                 fontSize: '10pt', 
                 lineHeight: '1.4',
                 color: '#000000',
                 backgroundColor: '#ffffff'
             }}
           >
              <h1 style={{ textAlign: "center", fontWeight: "bold", fontSize: "14pt", marginBottom: "20px", textDecoration: "underline" }}>DISCHARGE SUMMARY</h1>
              
              {/* PATIENT DETAILS TABLE */}
              <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000', marginBottom: "15px", fontSize: '9pt' }}>
                <tbody>
                  <tr>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold', width: '20%' }}>Patient Name:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', width: '30%' }}>{data.patient_details.patient_name || "-"}</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold', width: '20%' }}>UHID / Hospital ID:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', width: '30%' }}>{data.patient_details.uhid || "-"}</td>
                  </tr>
                  <tr>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold' }}>Age / Sex:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px' }}>{data.patient_details.age_sex || "-"}</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold' }}>Admission Date:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px' }}>{data.patient_details.admission_date || "-"}</td>
                  </tr>
                  <tr>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold' }}>Bed No:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px' }}>{data.patient_details.bed_no || "-"}</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold' }}>Discharge Date:</td>
                     <td style={{ border: '1px solid #000', padding: '4px 8px' }}>{data.patient_details.discharge_date || "-"}</td>
                  </tr>
                  <tr>
                     <td style={{ border: '1px solid #000', padding: '4px 8px', fontWeight: 'bold' }}>Consultant:</td>
                     <td colSpan={3} style={{ border: '1px solid #000', padding: '4px 8px' }}>{data.patient_details.consultant || "-"}</td>
                  </tr>
                </tbody>
              </table>

              {/* DIAGNOSIS */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>DIAGNOSIS:</h2>
                 <ul style={{ listStyleType: "square", paddingLeft: "20px", margin: 0 }}>
                   {data.diagnosis.primary?.length > 0 ? 
                     data.diagnosis.primary.map((d: string, i: number) => <li key={`p-${i}`}>{d}</li>) : 
                     <li>-</li>
                   }
                 </ul>
                 {data.diagnosis.associated_conditions?.length > 0 && (
                   <>
                     <h3 style={{ fontWeight: "bold", marginTop: "4px", marginBottom: "2px" }}>Associated Conditions:</h3>
                     <ul style={{ listStyleType: "circle", paddingLeft: "20px", margin: 0 }}>
                       {data.diagnosis.associated_conditions.map((d: string, i: number) => <li key={`a-${i}`}>{d}</li>)}
                     </ul>
                   </>
                 )}
              </div>

              {/* PRESENTING COMPLAINTS */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>PRESENTING COMPLAINTS:</h2>
                 <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000' }}>
                   <thead>
                     <tr>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left' }}>Complaint</th>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left', width: '30%' }}>Duration</th>
                     </tr>
                   </thead>
                   <tbody>
                     {data.presenting_complaints?.length > 0 ? data.presenting_complaints.map((c: any, i: number) => (
                       <tr key={i}>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{c.complaint || "-"}</td>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{c.duration || "-"}</td>
                       </tr>
                     )) : <tr><td colSpan={2} style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'center' }}>-</td></tr>}
                   </tbody>
                 </table>
              </div>

              {/* PAST HISTORY */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>PAST HISTORY:</h2>
                 <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000' }}>
                   <thead>
                     <tr>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left' }}>Condition</th>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left', width: '25%' }}>Duration</th>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left', width: '35%' }}>Remarks</th>
                     </tr>
                   </thead>
                   <tbody>
                     {data.past_history?.length > 0 ? data.past_history.map((h: any, i: number) => (
                       <tr key={i}>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{h.condition || "-"}</td>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{h.duration || "-"}</td>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{h.remarks || "-"}</td>
                       </tr>
                     )) : <tr><td colSpan={3} style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'center' }}>-</td></tr>}
                   </tbody>
                 </table>
              </div>

              {/* ALLERGIES */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", display: "inline-block", marginRight: "10px" }}>ALLERGIES:</h2>
                 <Checkbox 
                   value={data.allergies?.known === true} 
                   onChange={(val) => setData(prev => ({ ...prev, allergies: { ...prev.allergies, known: val } })) } 
                   label="Known" 
                 />
                 <Checkbox 
                   value={data.allergies?.known === false} 
                   onChange={(val) => setData(prev => ({ ...prev, allergies: { ...prev.allergies, known: !val } })) } 
                   label="Not Known" 
                 />
                 {data.allergies?.known && <span style={{ marginLeft: "10px" }}>Details: {data.allergies?.details}</span>}
              </div>

              {/* CLINICAL EXAMINATION */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>CLINICAL EXAMINATION:</h2>
                 <div style={{ border: '1px solid #000', padding: '6px' }}>
                   <div style={{ marginBottom: "6px" }}>
                     <span style={{ fontWeight: "bold", marginRight: "10px" }}>Vitals:</span>
                     Pulse: {data.clinical_exam?.vitals?.pulse || "-"} | 
                     BP: {data.clinical_exam?.vitals?.bp || "-"} | 
                     Temp: {data.clinical_exam?.vitals?.temperature || "-"} | 
                     RR: {data.clinical_exam?.vitals?.rr || "-"} | 
                     SpO2: {data.clinical_exam?.vitals?.spo2 || "-"}
                   </div>
                   <div style={{ marginBottom: "6px" }}>
                     <span style={{ fontWeight: "bold", marginRight: "10px" }}>General:</span>
                     <Checkbox 
                       value={!!data.clinical_exam?.general?.anaemia} 
                       onChange={(val) => setData(prev => ({ ...prev, clinical_exam: { ...prev.clinical_exam, general: { ...prev.clinical_exam.general, anaemia: val } } })) } 
                       label="Anaemia" 
                     />
                     <Checkbox 
                       value={!!data.clinical_exam?.general?.cyanosis} 
                       onChange={(val) => setData(prev => ({ ...prev, clinical_exam: { ...prev.clinical_exam, general: { ...prev.clinical_exam.general, cyanosis: val } } })) } 
                       label="Cyanosis" 
                     />
                     <Checkbox 
                       value={!!data.clinical_exam?.general?.clubbing} 
                       onChange={(val) => setData(prev => ({ ...prev, clinical_exam: { ...prev.clinical_exam, general: { ...prev.clinical_exam.general, clubbing: val } } })) } 
                       label="Clubbing" 
                     />
                     <Checkbox 
                       value={!!data.clinical_exam?.general?.jaundice} 
                       onChange={(val) => setData(prev => ({ ...prev, clinical_exam: { ...prev.clinical_exam, general: { ...prev.clinical_exam.general, jaundice: val } } })) } 
                       label="Jaundice" 
                     />
                     <Checkbox 
                       value={!!data.clinical_exam?.general?.oedema} 
                       onChange={(val) => setData(prev => ({ ...prev, clinical_exam: { ...prev.clinical_exam, general: { ...prev.clinical_exam.general, oedema: val } } })) } 
                       label="Oedema" 
                     />
                   </div>
                   <div>
                     <span style={{ fontWeight: "bold", marginRight: "10px" }}>Systemic:</span>
                     <ul style={{ margin: 0, paddingLeft: "30px", listStyleType: "none" }}>
                       <li><span style={{ fontWeight: "bold", marginRight: "5px" }}>CVS:</span> {data.clinical_exam?.systemic?.cardio || "-"}</li>
                       <li><span style={{ fontWeight: "bold", marginRight: "5px" }}>RS:</span> {data.clinical_exam?.systemic?.respiratory || "-"}</li>
                       <li><span style={{ fontWeight: "bold", marginRight: "5px" }}>GI:</span> {data.clinical_exam?.systemic?.gi || "-"}</li>
                       <li><span style={{ fontWeight: "bold", marginRight: "5px" }}>CNS:</span> {data.clinical_exam?.systemic?.cns || "-"}</li>
                     </ul>
                   </div>
                 </div>
              </div>

              {/* INVESTIGATIONS */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>INVESTIGATIONS:</h2>
                 <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000' }}>
                   <thead>
                     <tr>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left', width: '30%' }}>Test Name</th>
                       <th style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'left' }}>Findings</th>
                     </tr>
                   </thead>
                   <tbody>
                     {data.investigations?.length > 0 ? data.investigations.map((inv: any, i: number) => (
                       <tr key={i}>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{inv.name || "-"}</td>
                         <td style={{ border: '1px solid #000', padding: '2px 6px' }}>{inv.finding || "-"}</td>
                       </tr>
                     )) : <tr><td colSpan={2} style={{ border: '1px solid #000', padding: '2px 6px', textAlign: 'center' }}>-</td></tr>}
                   </tbody>
                 </table>
              </div>

              {/* PROCEDURES & HOSPITAL COURSE */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>PROCEDURAL NOTE:</h2>
                 <p style={{ margin: 0, paddingLeft: "10px", whiteSpace: "pre-wrap" }}>{data.procedures || "-"}</p>
              </div>
              
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>COURSE IN HOSPITAL:</h2>
                 <p style={{ margin: 0, paddingLeft: "10px", whiteSpace: "pre-wrap" }}>{data.hospital_course || "-"}</p>
              </div>

              {/* CONDITION AT DISCHARGE */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", display: "inline-block", marginRight: "10px" }}>CONDITION AT DISCHARGE:</h2>
                 <Checkbox 
                   value={!!data.condition_at_discharge?.stable} 
                   onChange={(val) => setData(prev => ({ ...prev, condition_at_discharge: { ...prev.condition_at_discharge, stable: val } })) } 
                   label="Stable" 
                 />
                 <Checkbox 
                   value={!!data.condition_at_discharge?.improved} 
                   onChange={(val) => setData(prev => ({ ...prev, condition_at_discharge: { ...prev.condition_at_discharge, improved: val } })) } 
                   label="Improved" 
                 />
                 <Checkbox 
                   value={!!data.condition_at_discharge?.referred} 
                   onChange={(val) => setData(prev => ({ ...prev, condition_at_discharge: { ...prev.condition_at_discharge, referred: val } })) } 
                   label="Referred" 
                 />
                 <Checkbox 
                   value={!!data.condition_at_discharge?.ama} 
                   onChange={(val) => setData(prev => ({ ...prev, condition_at_discharge: { ...prev.condition_at_discharge, ama: val } })) } 
                   label="LAMA" 
                 />
              </div>

              {/* MEDICATIONS */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>MEDICATIONS ON DISCHARGE:</h2>
                 <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000', fontSize: '9pt', textAlign: 'center' }}>
                   <thead>
                     <tr>
                       <th style={{ border: '1px solid #000', padding: '2px', width: '5%' }}>S.No</th>
                       <th style={{ border: '1px solid #000', padding: '2px', width: '5%' }}>Type</th>
                       <th style={{ border: '1px solid #000', padding: '2px' }}>Generic Name</th>
                       <th style={{ border: '1px solid #000', padding: '2px' }}>Brand Name</th>
                       <th style={{ border: '1px solid #000', padding: '2px' }}>Dose</th>
                       <th style={{ border: '1px solid #000', padding: '2px', width: '15%' }}>Frequency</th>
                       <th style={{ border: '1px solid #000', padding: '2px', width: '10%' }}>Duration</th>
                       <th style={{ border: '1px solid #000', padding: '2px', width: '20%' }}>Remarks</th>
                     </tr>
                   </thead>
                   <tbody>
                     {data.medications?.length > 0 ? data.medications.map((m: any, i: number) => {
                       const isFlagged = m.remarks?.includes("[REVIEW - possible IP med]");
                       const cleanRemarks = m.remarks?.replace("[REVIEW - possible IP med]", "").trim();
                       return (
                         <tr key={i} style={{ backgroundColor: isFlagged ? "#fff3cd" : "transparent" }}>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{i + 1}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.type || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.generic_name || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.brand_name || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.dose || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.frequency || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>{m.duration || "-"}</td>
                           <td style={{ border: '1px solid #000', padding: '2px' }}>
                             {cleanRemarks || "-"}
                             {isFlagged && <span style={{ color: "orange", marginLeft: "4px", fontSize: "8pt" }}>⚠ Review</span>}
                           </td>
                         </tr>
                       );
                     }) : (
                        <tr>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>1</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                          <td style={{ border: '1px solid #000', padding: '2px' }}>-</td>
                        </tr>
                      )}
                   </tbody>
                 </table>
              </div>

              {/* DIET & REHAB */}
              {(data.nutrition?.length > 0 || data.rehabilitation) && (
                <div style={{ marginBottom: "10px" }}>
                   {data.nutrition?.length > 0 && (
                     <>
                       <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>DIET/NUTRITION:</h2>
                       <ul style={{ listStyleType: "disc", paddingLeft: "20px", marginTop: "0" }}>
                         {data.nutrition.map((n: string, i: number) => <li key={`n-${i}`}>{n}</li>)}
                       </ul>
                     </>
                   )}
                   {data.rehabilitation && (
                     <>
                       <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>PHYSIOTHERAPY / REHABILITATION:</h2>
                       <p style={{ margin: 0, paddingLeft: "10px" }}>{data.rehabilitation}</p>
                     </>
                   )}
                </div>
              )}

              {/* PART 1: DYNAMIC TABLE (FROM AI) */}
              <div style={{ marginBottom: "10px" }}>
                 <h2 style={{ fontWeight: "bold", marginBottom: "4px" }}>FOLLOW UP INSTRUCTIONS:</h2>
                 <table style={{ width: "100%", borderCollapse: 'collapse', border: '1px solid #000', marginBottom: "15px" }}>
                   <thead>
                     <tr>
                       <th style={{ border: '1px solid #000', padding: '4px', textAlign: 'left', width: '30%' }}>Instruction</th>
                       <th style={{ border: '1px solid #000', padding: '4px', textAlign: 'left' }}>Details</th>
                     </tr>
                   </thead>
                   <tbody>
                     <tr>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>Follow-up Date</td>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>{data.follow_up?.follow_up_date || "-"}</td>
                     </tr>
                     <tr>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>Consultant</td>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>{data.follow_up?.recommended_doctor || "-"}</td>
                     </tr>
                     <tr>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>Reports to bring</td>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>{data.follow_up?.reports?.length > 0 ? data.follow_up.reports.join(", ") : "-"}</td>
                     </tr>
                     <tr>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>Tests advised</td>
                       <td style={{ border: '1px solid #000', padding: '4px' }}>{data.follow_up?.tests?.length > 0 ? data.follow_up.tests.join(", ") : "-"}</td>
                     </tr>
                   </tbody>
                 </table>
              </div>

              {/* PART 2: STATIC HOSPITAL BLOCK (HARDCODED) */}
              <div style={{ marginBottom: "15px", marginTop: "15px", fontSize: "10pt", lineHeight: "1.5" }}>
                 <p style={{ fontWeight: "bold", textAlign: "center", marginBottom: "15px" }}>
                   [PLEASE CONFIRM YOUR APPOINTMENT FOR FOLLOW UP FROM APPOINTMENT DESK - 9007666895]
                 </p>
                 <p style={{ marginBottom: "15px" }}>
                   For Medical query, contact Dr. {data.follow_up?.recommended_doctor || "______"}<br/>
                   For Other query contact Service care coordinator – 9051888973<br/>
                   For any Medicational query, contact Medication Nurse – 6292290663<br/>
                   (Timing: 10am–6pm Except Holiday)<br/>
                   For diet query, contact Dietician – 9007033037 (Timing 12pm–3pm)
                 </p>
                 <p style={{ fontWeight: "bold", marginBottom: "5px" }}>Please inform your Doctor before:</p>
                 <ul style={{ listStyleType: "disc", paddingLeft: "40px", marginTop: "0", marginBottom: "15px" }}>
                   <li>Changing medications</li>
                   <li>Dental/invasive procedures</li>
                 </ul>
                 <p style={{ fontWeight: "bold", marginBottom: "5px" }}>When to contact your Doctor, SOS:</p>
                 <ul style={{ listStyleType: "disc", paddingLeft: "40px", marginTop: "0", marginBottom: "15px" }}>
                   <li>Chest pain</li>
                   <li>Bleeding</li>
                   <li>Fever &gt; 101°F</li>
                   <li>Sugar variation</li>
                   <li>Leg swelling</li>
                   <li>Breathing issues</li>
                 </ul>
                 <p style={{ fontWeight: "bold", marginBottom: "15px" }}>Emergency Contact: 033-4088-4000</p>
                 <p style={{ fontStyle: "italic", fontSize: "9pt", marginBottom: "30px", fontWeight: "bold" }}>**Please revert if there is any typographical error.</p>
              </div>

              {/* PART 3: SIGNATURE BLOCK (ALWAYS) */}
              <div style={{ marginTop: '50px', display: 'flex', justifyContent: 'space-between', padding: '0 10px', fontSize: "10pt" }}>
                  <div style={{ textAlign: 'left' }}>
                     <p style={{ fontWeight: "bold", marginBottom: "5px" }}>RMO Signature:{' '.repeat(25)}</p>
                     <p style={{ fontWeight: "bold", marginBottom: "5px" }}>Registration No:{' '.repeat(25)}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                     <p style={{ fontWeight: "bold", marginBottom: "5px" }}>Consultant Doctor Name: {data.follow_up?.recommended_doctor || ""}</p>
                     <p style={{ marginBottom: "5px" }}>Consultant</p>
                     <br/>
                     <p style={{ fontWeight: "bold", marginBottom: "5px" }}>Medical Reg No:{' '.repeat(25)}</p>
                  </div>
              </div>

              {/* Footer Stamp */}
              <div style={{ marginTop: '40px', textAlign: 'center', fontSize: '8pt', color: '#444', borderTop: '1px solid #ccc', paddingTop: '10px' }}>
                 <p style={{ fontWeight: "bold", fontSize: "9pt", margin: 0 }}>{footerData.hospitalName}</p>
                 <p style={{ margin: 0 }}>{footerData.hospitalAddress} | Tel: {footerData.hospitalPhone}</p>
                 <p style={{ margin: 0, marginTop: "5px", fontStyle: "italic" }}>This is a computer generated document.</p>
              </div>
           </div>
         </div>
       </div>
       )}
    </div>
  );
}
