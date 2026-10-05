// Job Application Auto-Fill - Content Script

const FIELD_PATTERNS = {
  // Basic info
  first_name: [/first[_\s-]?name/i, /fname/i, /given[_\s-]?name/i, /name.*first/i],
  last_name: [/last[_\s-]?name/i, /lname/i, /surname/i, /family[_\s-]?name/i, /name.*last/i],
  full_name: [/full[_\s-]?name/i, /^name$/i, /your[_\s-]?name/i, /_systemfield_name/i],
  email: [/e?-?mail$/i, /email[_\s-]?address/i, /_systemfield_email/i],
  phone: [/phone[_\s-]?(number)?$/i, /mobile/i, /^tel$/i, /cell/i, /contact[_\s-]?number/i, /_systemfield_phone/i],
  phone_country_code: [/country[_\s-]?code/i, /phone.*code/i, /dial/i, /calling[_\s-]?code/i],

  // Location
  address_city: [/^city$/i, /town/i, /locality/i, /candidate[_\s-]?location/i, /location.*city/i],
  address_street: [/street/i, /address[_\s-]?line[_\s-]?1/i, /^address$/i, /address1/i],
  address_state: [/^state$/i, /province/i, /region/i],
  address_zip: [/zip/i, /postal/i, /postcode/i],
  address_country: [/^country$/i, /countries/i],

  // Professional links
  linkedin: [/linkedin/i, /linked[_\s-]?in/i],
  github: [/github/i, /git[_\s-]?hub/i],
  portfolio: [/portfolio/i, /^website$/i, /personal[_\s-]?(site|website|url)/i],

  // Work Experience
  experience_title: [/job[_\s-]?title/i, /position[_\s-]?title/i, /role[_\s-]?title/i, /^title$/i, /workexperience.*title/i],
  experience_company: [/company[_\s-]?(name)?$/i, /employer/i, /organization/i, /workexperience.*company/i],
  experience_location: [/work.*location/i, /job.*location/i, /workexperience.*location/i],
  experience_description: [/role[_\s-]?description/i, /job[_\s-]?description/i, /responsibilities/i, /description/i, /workexperience.*description/i],
  experience_start_date: [/start[_\s-]?date/i, /from[_\s-]?date/i, /workexperience.*start/i],
  experience_end_date: [/end[_\s-]?date/i, /to[_\s-]?date/i, /workexperience.*end/i],

  // Education - School/Degree
  education_school: [/school/i, /university/i, /college/i, /institution/i, /educational.*institution/i],
  education_degree: [/^degree/i, /degree[_\s-]?type/i, /level.*education/i],
  education_major: [/major/i, /field[_\s-]?of[_\s-]?study/i, /discipline/i, /concentration/i, /area.*study/i],
  education_gpa: [/^gpa$/i, /grade[_\s-]?point/i, /cumulative.*gpa/i],

  // Education - Dates (more specific patterns)
  education_start_year: [/start[_\s-]?(date[_\s-]?)?year/i, /from[_\s-]?year/i, /begin[_\s-]?year/i, /education.*start.*year/i],
  education_end_year: [/end[_\s-]?(date[_\s-]?)?year/i, /graduation[_\s-]?year/i, /to[_\s-]?year/i, /expected.*year/i, /anticipated.*graduation/i, /grad.*year/i],
  education_start_month: [/start[_\s-]?(date[_\s-]?)?month/i, /from[_\s-]?month/i, /begin[_\s-]?month/i],
  education_end_month: [/end[_\s-]?(date[_\s-]?)?month/i, /graduation[_\s-]?month/i, /to[_\s-]?month/i, /grad.*month/i],
  education_graduation_date: [/graduation[_\s-]?date/i, /expected[_\s-]?graduation/i, /anticipated[_\s-]?graduation/i, /when.*graduat/i],

  // High school
  high_school_name: [/high[_\s-]?school/i, /secondary[_\s-]?school/i],
  high_school_graduation: [/high[_\s-]?school.*(grad|year|date)/i, /secondary.*(grad|year)/i],

  // Test scores
  sat_score: [/\bsat\b/i, /sat[_\s-]?(score|total)/i],
  act_score: [/\bact\b/i, /act[_\s-]?(score|total)/i],
  gre_score: [/\bgre\b/i, /gre[_\s-]?(score|total)/i],

  // Work authorization
  authorized_to_work: [/authorized[_\s-]?to[_\s-]?work/i, /legally[_\s-]?(authorized|eligible)/i, /eligible[_\s-]?to[_\s-]?work/i, /work[_\s-]?authorization/i, /legal.*right.*work/i, /legally.*work/i],
  requires_sponsorship: [/sponsor/i, /visa[_\s-]?(sponsor|support)/i, /require.*sponsor/i, /need.*sponsor/i, /sponsorship.*need/i, /immigration/i],
  citizenship: [/citizenship/i, /citizen/i, /nationality/i],

  // Application questions
  applied_before: [/applied[_\s-]?(before|previously)/i, /previous[_\s-]?application/i, /have[_\s-]?you[_\s-]?applied/i, /prior.*application/i, /worked.*before/i, /previous.*employ/i],
  other_offers: [/other[_\s-]?offer/i, /competing[_\s-]?offer/i, /have[_\s-]?(any)?[_\s-]?offer/i, /current[_\s-]?(job)?[_\s-]?offer/i, /received.*offer/i],
  referral: [/referr/i, /hear[_\s-]?about/i, /how[_\s-]?did[_\s-]?you/i, /source/i, /how.*hear/i, /how.*find/i, /how.*learn/i],
  start_date_available: [/(available|earliest)[_\s-]?(start|begin)/i, /when[_\s-]?can[_\s-]?you[_\s-]?start/i, /availability/i],

  // Internship-specific
  full_time_interest: [/full[_\s-]?time/i, /after.*internship/i, /post[_\s-]?internship/i, /convert.*full/i],
  previous_internships: [/previous[_\s-]?internship/i, /prior[_\s-]?internship/i, /number.*internship/i, /how[_\s-]?many.*internship/i],
  education_year: [/education[_\s-]?status/i, /year[_\s-]?in[_\s-]?school/i, /class[_\s-]?year/i, /current[_\s-]?year/i, /year[_\s-]?1|year[_\s-]?2|year[_\s-]?3|year[_\s-]?4/i],
  further_education: [/further[_\s-]?education/i, /graduate[_\s-]?school/i, /pursuing.*degree/i, /plan.*education/i],
  office_location: [/office[_\s-]?location/i, /preferred[_\s-]?location/i, /work[_\s-]?location/i],
  team_preference: [/team[_\s-]?preference/i, /which[_\s-]?team/i, /role[_\s-]?selection/i],

  // Skills
  programming_languages: [/programming[_\s-]?language/i, /coding[_\s-]?language/i, /languages.*know/i, /proficient.*language/i],

  // EEOC
  gender: [/gender/i, /sex$/i, /gender[_\s-]?identity/i],
  race_ethnicity: [/race/i, /ethnicity/i, /ethnic/i],
  veteran_status: [/veteran/i, /military[_\s-]?service/i, /protected[_\s-]?veteran/i],
  disability_status: [/disability/i, /disabled/i, /accommodation/i],

  // Documents
  resume: [/resume/i, /cv\b/i, /curriculum/i, /_systemfield_resume/i],
  cover_letter: [/cover[_\s-]?letter/i, /motivation[_\s-]?letter/i, /message.*hiring/i],

  // Agreements (auto-check yes)
  privacy_agreement: [/privacy/i, /data[_\s-]?protection/i, /privacy[_\s-]?statement/i],
  privacy_statement: [/privacy[_\s-]?statement/i, /privacy[_\s-]?policy/i],
  interview_code_of_conduct: [/interview.*code.*conduct/i, /code.*conduct/i, /conduct.*agreement/i],
  nda_agreement: [/nda/i, /non[_\s-]?disclosure/i, /confidential/i],
  pursuing_further_education: [/further[_\s-]?education/i, /pursuing.*education/i, /graduate[_\s-]?school/i, /plan.*education/i],
};

function getFieldIdentifiers(element) {
  const name = element.getAttribute('name') || '';
  const id = element.getAttribute('id') || '';
  const placeholder = element.getAttribute('placeholder') || '';
  const ariaLabel = element.getAttribute('aria-label') || '';
  const labelText = getLabelText(element);

  return `${name} ${id} ${placeholder} ${ariaLabel} ${labelText}`.toLowerCase();
}

function getLabelText(element) {
  // Try label with 'for' attribute
  const id = element.getAttribute('id');
  if (id) {
    const label = document.querySelector(`label[for="${id}"]`);
    if (label) return label.textContent || '';
  }

  // Try parent label
  const parentLabel = element.closest('label');
  if (parentLabel) return parentLabel.textContent || '';

  // Try nearby elements
  const parent = element.parentElement;
  if (parent) {
    const prevSibling = element.previousElementSibling;
    if (prevSibling && prevSibling.tagName === 'LABEL') {
      return prevSibling.textContent || '';
    }
    // Check for label-like divs/spans
    const labelLike = parent.querySelector('label, .label, [class*="label"]');
    if (labelLike && labelLike !== element) {
      return labelLike.textContent || '';
    }
  }

  return '';
}

function matchField(identifiers, patterns) {
  for (const pattern of patterns) {
    if (pattern.test(identifiers)) {
      return true;
    }
  }
  return false;
}

function detectFieldType(element, identifiers) {
  for (const [fieldType, patterns] of Object.entries(FIELD_PATTERNS)) {
    if (matchField(identifiers, patterns)) {
      return fieldType;
    }
  }
  return null;
}

function getProfileValue(profile, fieldType) {
  // Address fields
  if (fieldType.startsWith('address_')) {
    const key = fieldType.replace('address_', '');
    return profile.address?.[key] || null;
  }

  // Education fields
  if (fieldType.startsWith('education_')) {
    const key = fieldType.replace('education_', '');
    const edu = profile.education?.[0];
    if (!edu) return null;

    if (key === 'school') return edu.school;
    if (key === 'degree') return edu.degree;
    if (key === 'major') return edu.major;
    if (key === 'gpa') return edu.gpa;
    if (key === 'end_year' || key === 'graduation_year' || key === 'graduation_date') {
      return edu.graduation_date?.split('-')[0] || null;
    }
    if (key === 'end_month' || key === 'graduation_month') {
      const parts = edu.graduation_date?.split('-');
      if (parts?.[1]) {
        const monthNum = parseInt(parts[1]);
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return months[monthNum - 1] || parts[1];
      }
      return null;
    }
    if (key === 'start_year') {
      return edu.start_date?.split('-')[0] || null;
    }
    if (key === 'start_month') {
      const parts = edu.start_date?.split('-');
      if (parts?.[1]) {
        const monthNum = parseInt(parts[1]);
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return months[monthNum - 1] || parts[1];
      }
      return null;
    }
    if (key === 'year') {
      // Calculate year in school from graduation
      const gradYear = parseInt(edu.graduation_date?.split('-')[0]);
      const currentYear = new Date().getFullYear();
      if (gradYear) {
        const yearsLeft = gradYear - currentYear;
        if (yearsLeft <= 0) return 'Graduated';
        if (yearsLeft === 1) return 'Year 4+';
        if (yearsLeft === 2) return 'Year 2-3';
        return 'Year 1';
      }
      return null;
    }
    return null;
  }

  // Work experience fields
  if (fieldType.startsWith('experience_')) {
    const key = fieldType.replace('experience_', '');
    const exp = profile.experience?.[0];
    if (!exp) return null;

    if (key === 'title') return exp.title;
    if (key === 'company') return exp.company;
    if (key === 'location') return exp.location;
    if (key === 'description') return exp.description;
    if (key === 'start_date') return exp.start_date;
    if (key === 'end_date') return exp.end_date;
    return null;
  }

  // High school fields
  if (fieldType.startsWith('high_school_')) {
    const key = fieldType.replace('high_school_', '');
    return profile.high_school?.[key] || null;
  }

  // Test scores
  if (fieldType.endsWith('_score')) {
    const key = fieldType.replace('_score', '');
    return profile.test_scores?.[key] || null;
  }

  // Yes/No fields
  if (fieldType === 'authorized_to_work') {
    return profile.authorized_to_work ? 'Yes' : 'No';
  }
  if (fieldType === 'requires_sponsorship') {
    return profile.requires_sponsorship ? 'Yes' : 'No';
  }
  if (fieldType === 'applied_before') {
    return profile.applied_before ? 'Yes' : 'No';
  }
  if (fieldType === 'other_offers') {
    return profile.other_offers ? 'Yes' : 'No';
  }
  if (fieldType === 'full_time_interest') {
    return profile.full_time_interest !== false ? 'Yes' : 'No';
  }
  if (fieldType === 'further_education') {
    return profile.further_education ? 'Yes' : 'No';
  }
  if (fieldType === 'privacy_agreement' || fieldType === 'nda_agreement') {
    return 'Yes';
  }
  if (fieldType === 'privacy_statement') {
    return profile.privacy_statement || 'I agree';
  }
  if (fieldType === 'interview_code_of_conduct') {
    return profile.interview_code_of_conduct || 'I agree';
  }
  if (fieldType === 'pursuing_further_education') {
    return profile.pursuing_further_education || null;
  }

  // Full name
  if (fieldType === 'full_name') {
    if (profile.first_name && profile.last_name) {
      return `${profile.first_name} ${profile.last_name}`;
    }
    return null;
  }

  // Phone country code
  if (fieldType === 'phone_country_code') {
    return profile.phone_country_code || '+1';
  }

  // Programming languages
  if (fieldType === 'programming_languages') {
    const skills = profile.skills || profile.programming_languages;
    if (Array.isArray(skills)) {
      return skills.filter(s =>
        /python|java|javascript|typescript|c\+\+|c#|go|rust|ruby|sql|html|css|bash|ocaml/i.test(s)
      ).join(', ');
    }
    return null;
  }

  // Direct fields
  return profile[fieldType] || null;
}

function analyzeForm() {
  const fields = [];
  const fileUploads = [];

  // Find all input fields
  const inputs = document.querySelectorAll(
    'input[type="text"], input[type="email"], input[type="tel"], ' +
    'input[type="url"], input[type="number"], input:not([type]), textarea'
  );

  inputs.forEach(element => {
    if (!isVisible(element)) return;
    if (element.type === 'hidden' || element.type === 'submit' || element.type === 'button') return;

    const identifiers = getFieldIdentifiers(element);
    const fieldType = detectFieldType(element, identifiers);

    if (fieldType) {
      fields.push({
        element,
        fieldType,
        label: getLabelText(element) || element.placeholder || element.name || fieldType,
        identifiers
      });
    }
  });

  // Find select fields
  const selects = document.querySelectorAll('select');
  selects.forEach(element => {
    if (!isVisible(element)) return;

    const identifiers = getFieldIdentifiers(element);
    const fieldType = detectFieldType(element, identifiers);

    if (fieldType) {
      fields.push({
        element,
        fieldType,
        label: getLabelText(element) || element.name || fieldType,
        identifiers,
        isSelect: true
      });
    }
  });

  // Find file uploads
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(element => {
    const identifiers = getFieldIdentifiers(element);
    let uploadType = 'other';

    if (/resume|cv/i.test(identifiers)) {
      uploadType = 'resume';
    } else if (/cover/i.test(identifiers)) {
      uploadType = 'cover_letter';
    }

    fileUploads.push({
      element,
      type: uploadType,
      label: getLabelText(element) || uploadType
    });
  });

  return { fields, fileUploads };
}

function isVisible(element) {
  if (!element) return false;
  const style = window.getComputedStyle(element);
  return style.display !== 'none' &&
         style.visibility !== 'hidden' &&
         style.opacity !== '0' &&
         element.offsetParent !== null;
}

function fillField(element, value, isSelect = false) {
  if (!value) return false;

  try {
    if (isSelect) {
      // Try to find matching option
      const options = Array.from(element.options);
      const valueStr = String(value).toLowerCase();

      // Try exact match first
      let match = options.find(opt =>
        opt.value.toLowerCase() === valueStr ||
        opt.textContent.toLowerCase().trim() === valueStr
      );

      // Try partial match
      if (!match) {
        match = options.find(opt =>
          opt.value.toLowerCase().includes(valueStr) ||
          opt.textContent.toLowerCase().includes(valueStr) ||
          valueStr.includes(opt.value.toLowerCase()) ||
          valueStr.includes(opt.textContent.toLowerCase().trim())
        );
      }

      if (match) {
        element.value = match.value;
        element.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }
      return false;
    } else {
      // Text input
      element.focus();
      element.value = value;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      element.blur();
      return true;
    }
  } catch (e) {
    console.error('Error filling field:', e);
    return false;
  }
}

function fillForm(profile) {
  const { fields, fileUploads } = analyzeForm();
  const results = { filled: [], skipped: [], errors: [] };

  fields.forEach(({ element, fieldType, label, isSelect }) => {
    const value = getProfileValue(profile, fieldType);

    if (value) {
      const success = fillField(element, value, isSelect);
      if (success) {
        results.filled.push({ label, value, fieldType });
      } else {
        results.errors.push({ label, value, fieldType, reason: 'Could not set value' });
      }
    } else {
      results.skipped.push({ label, fieldType, reason: 'No value in profile' });
    }
  });

  return { results, fileUploads };
}

function analyzeAllFields() {
  // Get ALL form fields, not just matched ones
  const allFields = [];

  const inputs = document.querySelectorAll(
    'input[type="text"], input[type="email"], input[type="tel"], ' +
    'input[type="url"], input[type="number"], input:not([type]), textarea, select'
  );

  inputs.forEach(element => {
    if (!isVisible(element)) return;
    if (element.type === 'hidden' || element.type === 'submit' || element.type === 'button') return;

    const identifiers = getFieldIdentifiers(element);
    const fieldType = detectFieldType(element, identifiers);
    const label = getLabelText(element) || element.placeholder || element.name || element.id || '(no label)';

    allFields.push({
      label: label.substring(0, 50),
      identifiers: identifiers.substring(0, 100),
      matched: !!fieldType,
      fieldType: fieldType || null,
      tagName: element.tagName.toLowerCase(),
      type: element.type || 'text'
    });
  });

  return allFields;
}

// Generate a unique selector for an element
function generateSelector(element) {
  if (element.id) {
    return `#${CSS.escape(element.id)}`;
  }
  if (element.name) {
    const tagName = element.tagName.toLowerCase();
    return `${tagName}[name="${CSS.escape(element.name)}"]`;
  }
  // Fallback: use tag + position
  const parent = element.parentElement;
  if (!parent) return element.tagName.toLowerCase();

  const siblings = Array.from(parent.children).filter(
    c => c.tagName === element.tagName
  );
  const index = siblings.indexOf(element);
  if (siblings.length === 1) {
    return `${generateSelector(parent)} > ${element.tagName.toLowerCase()}`;
  }
  return `${generateSelector(parent)} > ${element.tagName.toLowerCase()}:nth-of-type(${index + 1})`;
}

// Extract all form fields with comprehensive info for LLM matching
function extractAllFieldsForLLM() {
  const fields = [];

  // Text inputs and textareas
  const inputs = document.querySelectorAll(
    'input[type="text"], input[type="email"], input[type="tel"], ' +
    'input[type="url"], input[type="number"], input:not([type]), textarea'
  );

  let fieldIndex = 0;
  inputs.forEach(element => {
    if (!isVisible(element)) return;
    if (element.type === 'hidden' || element.type === 'submit' || element.type === 'button') return;

    const label = getLabelText(element);
    fields.push({
      index: fieldIndex++,
      selector: generateSelector(element),
      label: label || '',
      name: element.name || '',
      id: element.id || '',
      placeholder: element.placeholder || '',
      type: element.type || 'text',
      tagName: 'input',
      required: element.required || element.getAttribute('aria-required') === 'true',
      currentValue: element.value || ''
    });
  });

  // Select elements
  const selects = document.querySelectorAll('select');
  selects.forEach(element => {
    if (!isVisible(element)) return;

    const label = getLabelText(element);
    const options = Array.from(element.options)
      .filter(opt => opt.value && opt.value !== '')
      .map(opt => opt.textContent.trim())
      .slice(0, 20); // Limit options to avoid token bloat

    fields.push({
      index: fieldIndex++,
      selector: generateSelector(element),
      label: label || '',
      name: element.name || '',
      id: element.id || '',
      type: 'select',
      tagName: 'select',
      options: options,
      required: element.required || element.getAttribute('aria-required') === 'true',
      currentValue: element.value || ''
    });
  });

  // Radio button groups
  const radioGroups = {};
  document.querySelectorAll('input[type="radio"]').forEach(element => {
    if (!isVisible(element)) return;
    const name = element.name;
    if (!name) return;

    if (!radioGroups[name]) {
      radioGroups[name] = {
        selector: `input[name="${CSS.escape(name)}"]`,
        label: getLabelText(element) || '',
        name: name,
        type: 'radio',
        tagName: 'input',
        options: [],
        required: element.required
      };
    }

    const optionLabel = getLabelText(element) ||
      element.nextSibling?.textContent?.trim() ||
      element.value;
    if (optionLabel && !radioGroups[name].options.includes(optionLabel)) {
      radioGroups[name].options.push(optionLabel);
    }
  });

  Object.values(radioGroups).forEach(group => {
    fields.push(group);
  });

  return fields;
}

// Get profile value by dot-notation key (e.g., "address.city")
function getProfileValueByKey(profile, key) {
  // Handle dot notation
  if (key.includes('.')) {
    const [parent, child] = key.split('.');

    if (parent === 'address') {
      return profile.address?.[child] || null;
    }
    if (parent === 'education') {
      const edu = profile.education?.[0];
      if (!edu) return null;

      if (child === 'school') return edu.school;
      if (child === 'degree') return edu.degree;
      if (child === 'major') return edu.major;
      if (child === 'gpa') return edu.gpa;
      if (child === 'end_year') {
        return edu.graduation_date?.split('-')[0] || null;
      }
      if (child === 'end_month') {
        const parts = edu.graduation_date?.split('-');
        if (parts?.[1]) {
          const monthNum = parseInt(parts[1]);
          const months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December'];
          return months[monthNum - 1] || parts[1];
        }
        return null;
      }
      if (child === 'start_year') {
        return edu.start_date?.split('-')[0] || null;
      }
      if (child === 'start_month') {
        const parts = edu.start_date?.split('-');
        if (parts?.[1]) {
          const monthNum = parseInt(parts[1]);
          const months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December'];
          return months[monthNum - 1] || parts[1];
        }
        return null;
      }
      return null;
    }
    if (parent === 'high_school') {
      return profile.high_school?.[child] || null;
    }
    if (parent === 'test_scores') {
      return profile.test_scores?.[child] || null;
    }
    if (parent === 'experience') {
      // Handle indexed experience like experience.0.title, experience.1.company
      const parts = key.split('.');
      if (parts.length === 3) {
        const index = parseInt(parts[1]);
        const field = parts[2];
        const exp = profile.experience?.[index];
        if (!exp) return null;
        if (field === 'title') return exp.title;
        if (field === 'company') return exp.company;
        if (field === 'location') return exp.location;
        if (field === 'description') return exp.description;
        if (field === 'start_date') return exp.start_date;
        if (field === 'end_date') return exp.end_date;
        return null;
      }
      // Fallback for experience.title (no index) - use first experience
      const exp = profile.experience?.[0];
      if (!exp) return null;
      if (child === 'title') return exp.title;
      if (child === 'company') return exp.company;
      if (child === 'location') return exp.location;
      if (child === 'description') return exp.description;
      if (child === 'start_date') return exp.start_date;
      if (child === 'end_date') return exp.end_date;
      return null;
    }
    return null;
  }

  // Direct keys
  if (key === 'full_name') {
    if (profile.first_name && profile.last_name) {
      return `${profile.first_name} ${profile.last_name}`;
    }
    return null;
  }

  if (key === 'authorized_to_work') {
    return profile.authorized_to_work ? 'Yes' : 'No';
  }
  if (key === 'requires_sponsorship') {
    return profile.requires_sponsorship ? 'Yes' : 'No';
  }
  if (key === 'applied_before') {
    return profile.applied_before ? 'Yes' : 'No';
  }
  if (key === 'other_offers') {
    return profile.other_offers ? 'Yes' : 'No';
  }

  if (key === 'skills') {
    const skills = profile.skills || profile.programming_languages;
    if (Array.isArray(skills)) {
      return skills.filter(s =>
        /python|java|javascript|typescript|c\+\+|c#|go|rust|ruby|sql|html|css|bash|ocaml/i.test(s)
      ).join(', ');
    }
    return null;
  }

  return profile[key] || null;
}

// Fill form using LLM-provided mapping
function fillFormWithMapping(mapping, profile) {
  const results = { filled: [], skipped: [], errors: [] };

  for (const [selector, profileKey] of Object.entries(mapping)) {
    if (!profileKey) continue;

    try {
      const element = document.querySelector(selector);
      if (!element) {
        results.errors.push({
          selector,
          profileKey,
          reason: 'Element not found'
        });
        continue;
      }

      const value = getProfileValueByKey(profile, profileKey);
      if (!value) {
        results.skipped.push({
          selector,
          profileKey,
          label: getLabelText(element) || selector,
          reason: 'No value in profile'
        });
        continue;
      }

      const isSelect = element.tagName.toLowerCase() === 'select';
      const isRadio = element.type === 'radio';

      let success = false;

      if (isRadio) {
        // Handle radio buttons
        const radios = document.querySelectorAll(`input[name="${element.name}"]`);
        const valueStr = String(value).toLowerCase();

        for (const radio of radios) {
          const radioLabel = (getLabelText(radio) || radio.value || '').toLowerCase();
          if (radioLabel.includes(valueStr) || valueStr.includes(radioLabel) ||
              radio.value.toLowerCase() === valueStr) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change', { bubbles: true }));
            success = true;
            break;
          }
        }
      } else {
        success = fillField(element, value, isSelect);
      }

      if (success) {
        results.filled.push({
          selector,
          profileKey,
          label: getLabelText(element) || selector,
          value
        });
      } else {
        results.errors.push({
          selector,
          profileKey,
          label: getLabelText(element) || selector,
          reason: 'Could not set value'
        });
      }
    } catch (e) {
      results.errors.push({
        selector,
        profileKey,
        reason: e.message
      });
    }
  }

  return results;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'ping') {
    sendResponse({ status: 'ok' });
    return true;
  }

  if (request.action === 'analyze') {
    const { fields, fileUploads } = analyzeForm();

    // Get profile to show what would be filled
    chrome.storage.sync.get(['profile'], (data) => {
      const profile = data.profile || {};

      const fieldInfo = fields.map(({ fieldType, label }) => ({
        fieldType,
        label,
        value: getProfileValue(profile, fieldType),
        hasValue: !!getProfileValue(profile, fieldType)
      }));

      const uploadInfo = fileUploads.map(({ type, label }) => ({
        type,
        label
      }));

      sendResponse({
        fields: fieldInfo,
        fileUploads: uploadInfo,
        url: window.location.href
      });
    });

    return true; // Keep channel open for async response
  }

  if (request.action === 'debug') {
    const allFields = analyzeAllFields();
    sendResponse({ allFields, url: window.location.href });
    return true;
  }

  if (request.action === 'fill') {
    chrome.storage.sync.get(['profile'], (data) => {
      const profile = data.profile || {};
      const { results, fileUploads } = fillForm(profile);
      sendResponse({ results, fileUploads });
    });

    return true;
  }

  if (request.action === 'fillSingle') {
    const { fieldType, value } = request;
    const { fields } = analyzeForm();
    const field = fields.find(f => f.fieldType === fieldType);

    if (field) {
      const success = fillField(field.element, value, field.isSelect);
      sendResponse({ success });
    } else {
      sendResponse({ success: false, error: 'Field not found' });
    }

    return true;
  }

  // LLM-based field extraction
  if (request.action === 'extractFieldsForLLM') {
    const fields = extractAllFieldsForLLM();
    sendResponse({
      fields,
      url: window.location.href
    });
    return true;
  }

  // LLM-based form filling
  if (request.action === 'fillWithMapping') {
    const { mapping } = request;

    chrome.storage.sync.get(['profile'], (data) => {
      const profile = data.profile || {};
      const results = fillFormWithMapping(mapping, profile);
      sendResponse({ results });
    });

    return true;
  }
});
