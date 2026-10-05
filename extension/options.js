// Job Application Auto-Fill - Options Script

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('profileForm');
  const toast = document.getElementById('toast');
  const exportBtn = document.getElementById('exportBtn');
  const importBtn = document.getElementById('importBtn');
  const importFile = document.getElementById('importFile');
  const resetBtn = document.getElementById('resetBtn');

  // Load existing profile
  const { profile } = await chrome.storage.sync.get(['profile']);
  if (profile) {
    loadProfileToForm(profile);
  }

  function loadProfileToForm(profile) {
    // Basic fields
    setValue('first_name', profile.first_name);
    setValue('last_name', profile.last_name);
    setValue('email', profile.email);
    setValue('phone', profile.phone);
    setValue('phone_country_code', profile.phone_country_code);

    // Address
    setValue('address_street', profile.address?.street);
    setValue('address_city', profile.address?.city);
    setValue('address_state', profile.address?.state);
    setValue('address_zip', profile.address?.zip);
    setValue('address_country', profile.address?.country);

    // Links
    setValue('linkedin', profile.linkedin);
    setValue('github', profile.github);
    setValue('portfolio', profile.portfolio);

    // Education
    const edu = profile.education?.[0];
    if (edu) {
      setValue('edu_school', edu.school);
      setValue('edu_degree', edu.degree);
      setValue('edu_major', edu.major);
      setValue('edu_gpa', edu.gpa);
      setValue('edu_graduation', edu.graduation_date);
      setValue('edu_start', edu.start_date);
    }

    // High school
    setValue('hs_name', profile.high_school?.name);
    setValue('hs_graduation', profile.high_school?.graduation);

    // Test scores
    setValue('sat_score', profile.test_scores?.sat);
    setValue('act_score', profile.test_scores?.act);

    // Work experience (3 entries)
    for (let i = 0; i < 3; i++) {
      const exp = profile.experience?.[i];
      if (exp) {
        setValue(`exp${i+1}_title`, exp.title);
        setValue(`exp${i+1}_company`, exp.company);
        setValue(`exp${i+1}_location`, exp.location);
        setValue(`exp${i+1}_start`, exp.start_date);
        setValue(`exp${i+1}_end`, exp.end_date);
        setValue(`exp${i+1}_description`, exp.description);
      }
    }

    // Work authorization
    setChecked('authorized_to_work', profile.authorized_to_work);
    setChecked('requires_sponsorship', profile.requires_sponsorship);
    setValue('citizenship', profile.citizenship);

    // EEOC
    setValue('gender', profile.gender);
    setValue('race_ethnicity', profile.race_ethnicity);
    setValue('veteran_status', profile.veteran_status);
    setValue('disability_status', profile.disability_status);

    // Application defaults
    setChecked('applied_before', profile.applied_before);
    setChecked('other_offers', profile.other_offers);
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
      el.value = value;
    }
  }

  function setChecked(id, value) {
    const el = document.getElementById(id);
    if (el) {
      el.checked = !!value;
    }
  }

  function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
  }

  function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
  }

  function getFormProfile() {
    return {
      first_name: getValue('first_name'),
      last_name: getValue('last_name'),
      email: getValue('email'),
      phone: getValue('phone'),
      phone_country_code: getValue('phone_country_code') || '+1',

      address: {
        street: getValue('address_street'),
        city: getValue('address_city'),
        state: getValue('address_state'),
        zip: getValue('address_zip'),
        country: getValue('address_country') || 'United States',
      },

      linkedin: getValue('linkedin'),
      github: getValue('github'),
      portfolio: getValue('portfolio'),

      education: [{
        school: getValue('edu_school'),
        degree: getValue('edu_degree'),
        major: getValue('edu_major'),
        gpa: getValue('edu_gpa'),
        graduation_date: getValue('edu_graduation'),
        start_date: getValue('edu_start'),
      }],

      experience: [
        {
          title: getValue('exp1_title'),
          company: getValue('exp1_company'),
          location: getValue('exp1_location'),
          start_date: getValue('exp1_start'),
          end_date: getValue('exp1_end'),
          description: getValue('exp1_description'),
        },
        {
          title: getValue('exp2_title'),
          company: getValue('exp2_company'),
          location: getValue('exp2_location'),
          start_date: getValue('exp2_start'),
          end_date: getValue('exp2_end'),
          description: getValue('exp2_description'),
        },
        {
          title: getValue('exp3_title'),
          company: getValue('exp3_company'),
          location: getValue('exp3_location'),
          start_date: getValue('exp3_start'),
          end_date: getValue('exp3_end'),
          description: getValue('exp3_description'),
        },
      ].filter(exp => exp.title || exp.company),

      high_school: {
        name: getValue('hs_name'),
        graduation: getValue('hs_graduation'),
      },

      test_scores: {
        sat: getValue('sat_score'),
        act: getValue('act_score'),
      },

      authorized_to_work: getChecked('authorized_to_work'),
      requires_sponsorship: getChecked('requires_sponsorship'),
      citizenship: getValue('citizenship'),

      gender: getValue('gender'),
      race_ethnicity: getValue('race_ethnicity'),
      veteran_status: getValue('veteran_status'),
      disability_status: getValue('disability_status'),

      applied_before: getChecked('applied_before'),
      other_offers: getChecked('other_offers'),
    };
  }

  function showToast(message, isError = false) {
    toast.textContent = message;
    toast.className = 'toast' + (isError ? ' error' : '');
    toast.style.display = 'block';

    setTimeout(() => {
      toast.style.display = 'none';
    }, 3000);
  }

  // Save form
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const profile = getFormProfile();

    try {
      await chrome.storage.sync.set({ profile });
      showToast('Profile saved successfully!');
    } catch (error) {
      console.error('Error saving profile:', error);
      showToast('Error saving profile', true);
    }
  });

  // Export profile
  exportBtn.addEventListener('click', async () => {
    const profile = getFormProfile();
    const blob = new Blob([JSON.stringify(profile, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'job-autofill-profile.json';
    a.click();

    URL.revokeObjectURL(url);
    showToast('Profile exported!');
  });

  // Import profile
  importBtn.addEventListener('click', () => {
    importFile.click();
  });

  importFile.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const profile = JSON.parse(text);

      loadProfileToForm(profile);
      await chrome.storage.sync.set({ profile });

      showToast('Profile imported successfully!');
    } catch (error) {
      console.error('Error importing profile:', error);
      showToast('Error importing profile. Make sure it\'s a valid JSON file.', true);
    }

    // Reset file input
    importFile.value = '';
  });

  // Reset to default
  resetBtn.addEventListener('click', async () => {
    if (confirm('Are you sure you want to reset your profile? This cannot be undone.')) {
      await chrome.storage.sync.remove(['profile']);
      form.reset();
      showToast('Profile reset to default');
    }
  });
});
