-- Sample data for dockets and document and cfrParts

-- =========================================
-- DOCKETS
-- =========================================

INSERT INTO dockets (
    docket_id,
    docket_api_link,
    agency_id,
    docket_category,
    docket_type,
    effective_date,
    flex_field1,
    flex_field2,
    modify_date,
    organization,
    petition_nbr,
    program,
    rin,
    short_title,
    flex_subtype1,
    flex_subtype2,
    docket_title,
    docket_abstract
) VALUES (
    'CMS-2025-0240',
    'https://api.regulations.gov/v4/dockets/CMS-2025-0240',
    'CMS',
    NULL,
    'Rulemaking',
    NULL,
    NULL,
    NULL,
    '2025-11-24T16:44:12Z',
    NULL,
    NULL,
    NULL,
    '0938-AV52',
    NULL,
    NULL,
    NULL,
    'CY 2026 Changes to the End-Stage Renal Disease (ESRD) Prospective Payment System and Quality Incentive Program.  CMS-1830-P',
    'This proposed rule would update and revise the End-Stage Renal Disease (ESRD) Prospective Payment System for calendar year 2026.  This rule also proposes to update the payment rate for renal dialysis services furnished by an ESRD facility to individuals with acute kidney injury.  In addition, this rule proposes to update requirements for the ESRD Quality Incentive Program and to terminate and modify requirements for the ESRD Treatment Choices Model.'
);

INSERT INTO dockets (
    docket_id,
    docket_api_link,
    agency_id,
    docket_category,
    docket_type,
    effective_date,
    flex_field1,
    flex_field2,
    modify_date,
    organization,
    petition_nbr,
    program,
    rin,
    short_title,
    flex_subtype1,
    flex_subtype2,
    docket_title,
    docket_abstract
) VALUES (
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/dockets/CMS-2025-0304',
    'CMS',
    NULL,
    'Rulemaking',
    NULL,
    NULL,
    NULL,
    '2025-11-28T17:04:15Z',
    NULL,
    NULL,
    NULL,
    '0938-AV50',
    NULL,
    NULL,
    NULL,
    'CY 2026 Payment Policies under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies (CMS-1832-P)',
    'This proposed rule addresses changes to the physician fee schedule and  Medicare Part B payment policies to ensure that payment systems are updated to reflect changes in medical practice, relative value of services, and changes in the statute; codification of new policies for the Medicare Prescription Drug Inflation Rebate Program under the Inflation Reduction Act of 2022; the Ambulatory Specialty Model; updates to the Medicare Diabetes Prevention Program expanded model; updates to drugs and biological products paid under Part B; Medicare Shared Savings Program requirements; updates to the Quality Payment Program; updates to policies for Rural Health Clinics and Federally Qualified Health Centers update to the Ambulance Fee Schedule regulations; codification of the Inflation Reduction Act and Consolidated Appropriations Act, 2023 provisions; and updates to the Medicare Promoting Interoperability Program.'
);

-- =========================================
-- DOCUMENTS
-- =========================================

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0304-0001',
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/documents/CMS-2025-0304-0001',
    NULL,
    NULL,
    'CMS',
    FALSE, --idk this didn't have data (is_late_comment)
    NULL,
    NULL, -- comment_category had no data
    NULL,
    NULL,
    '2025-07-18T03:59:59Z',
    '2025-07-14T04:00:00Z',
    NULL,
    'Proposed Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-07-18T09:00:30Z',
    FALSE,
    NULL,
    NULL,
    '2025-07-14T04:00:00Z',
    NULL,
    NULL,
    '2025-07-13T00:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Medicare and Medicaid Programs; CY 2026 Payment Policies under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies; Medicare Shared Savings Program Requirements; and Medicare Prescription Drug Inflation Rebate Program (CMS-1832-P)',
    NULL,
    FALSE,
    NULL
);

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0304-0009',
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/documents/CMS-2025-0304-0009',
    NULL,
    NULL,
    'CMS',
    FALSE, --idk this didn't have data (is_late_comment)
    NULL,
    NULL, -- comment_category had no data
    NULL,
    NULL,
    '2025-09-13T03:59:59Z',
    '2025-07-16T04:00:00Z',
    NULL,
    'Proposed Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-09-19T09:01:18Z',
    FALSE,
    NULL,
    NULL,
    '2025-07-16T04:00:00Z',
    NULL,
    NULL,
    '2025-07-16T04:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Medicare and Medicaid Programs: Calendar Year 2026 Payment Policies under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies; Medicare Shared Savings Program Requirements; and Medicare Prescription Drug Inflation Rebate Program',
    ARRAY[
        'Administrative Practices and Procedures',
        'Health Facilities',
        'Health Professions',
        'Medical Devices',
        'Medicare',
        'Reporting and Recordkeeping Requirements',
        'Rural Areas',
        'X-Rays',
        'Laboratories',
        'Biologics',
        'Drugs',
        'Emergency Medical Services',
        'Prescription Drugs',
        'Health Maintenance Organizations (HMO)',
        'Health Records',
        'Medicaid',
        'Penalties',
        'Privacy',
        'Health Care',
        'Health Insurance',
        'Intergovernmental Relations'
        ],
    FALSE,
    NULL
);

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0304-1544',
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/documents/CMS-2025-0304-1544',
    NULL,
    NULL,
    'CMS',
    FALSE,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-09-13T03:59:59Z',
    '2025-08-14T04:00:00Z',
    NULL,
    'Proposed Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-09-16T09:00:30Z',
    FALSE,
    NULL,
    NULL,
    '2025-08-14T04:00:00Z',
    NULL,
    NULL,
    '2025-08-14T04:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Medicare and Medicaid Programs: Calendar Year 2026 Payment Policies under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies; Medicare Shared Savings Program Requirements; and Medicare Prescription Drug Inflation Rebate Program; Correction',
    NULL,
    FALSE,
    NULL
);

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0304-14108',
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/documents/CMS-2025-0304-14108',
    NULL,
    NULL,
    'CMS',
    FALSE,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-09-13T03:59:59Z',
    '2025-08-14T04:00:00Z',
    NULL,
    'Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-11-06T18:23:15Z',
    FALSE,
    NULL,
    NULL,
    '2025-11-05T05:00:00Z',
    NULL,
    NULL,
    '2025-11-05T05:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Medicare and Medicaid Programs: Calendar Year 2026 Payment Policies under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies; Medicare Shared Savings Program Requirements; and Medicare Prescription Drug Inflation Rebate Program',
    ARRAY[
        'Administrative Practices and Procedures',
        'Health Facilities',
        'Health Professions',
        'Medical Devices',
        'Medicare',
        'Reporting and Recordkeeping Requirements',
        'Rural Areas',
        'X-Rays',
        'Laboratories',
        'Biologics',
        'Drugs',
        'Emergency Medical Services',
        'Prescription Drugs',
        'Health Maintenance Organizations (HMO)',
        'Health Records',
        'Medicaid',
        'Penalties',
        'Privacy',
        'Health Care',
        'Health Insurance',
        'Intergovernmental Relations'
        ],
    FALSE,
    NULL
);

INSERT INTO documents (
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0304-14109',
    'CMS-2025-0304',
    'https://api.regulations.gov/v4/documents/CMS-2025-0304-14109',
    NULL,
    NULL,
    'CMS',
    FALSE,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-11-28T22:04:36Z',
    FALSE,
    NULL,
    NULL,
    '2025-11-28T05:00:00Z',
    NULL,
    NULL,
    '2025-11-28T05:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'Medicare and Medicaid Programs: Calendar Year 2026 Payment Policies Under the Physician Fee Schedule and Other Changes to Part B Payment and Coverage Policies; Medicare Shared Savings Program Requirements; and Medicare Prescription Drug Inflation Rebate Program; Correction',
    NULL,
    FALSE,
    NULL
);

INSERT INTO documents(
    document_id,
    docket_id,
    document_api_link,
    address1,
    address2,
    agency_id,
    is_late_comment,
    author_date,
    comment_category,
    city,
    comment,
    comment_end_date,
    comment_start_date,
    country,
    document_type,
    effective_date,
    email,
    fax,
    flex_field1,
    flex_field2,
    first_name,
    submitter_gov_agency,
    submitter_gov_agency_type,
    implementation_date,
    last_name,
    modify_date,
    is_open_for_comment,
    submitter_org,
    phone,
    posted_date,
    postmark_date,
    reason_withdrawn,
    receive_date,
    reg_writer_instruction,
    restriction_reason,
    restriction_reason_type,
    state_province_region,
    subtype,
    document_title,
    topics,
    is_withdrawn,
    postal_code
) VALUES (
    'CMS-2025-0240-0001',
    'CMS-2025-0240',
    'https://api.regulations.gov/v4/documents/CMS-2025-0240-0001',
    NULL,
    NULL,
    'CMS',
    FALSE,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-07-03T03:59:59Z',
    '2025-06-30T04:00:00Z',
    NULL,
    'Proposed Rule',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2025-07-02T16:46:00Z',
    FALSE,
    NULL,
    NULL,
    '2025-06-30T04:00:00Z',
    NULL,
    NULL,
    '2025-06-30T04:00:00Z',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'CY 2026 Changes to the End-Stage Renal Disease (ESRD) Prospective Payment System and Quality Incentive Program. CMS1830-P Display',
    NULL,
    FALSE,
    NULL
);

-- =========================================
-- LINKS
-- =========================================

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    405,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-405?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    410,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-410?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    413,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-413?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    414,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-414?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    424,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-424?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    425,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-425?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    427,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-427?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    428,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-428?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    495,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-495?toc=1'
);

INSERT INTO links(
    title,
    cfrPart,
    link
) VALUES (
    42,
    512,
    'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-H/part-512?toc=1'
);

-- =========================================
-- CFR PARTS
-- =========================================

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '405'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '410'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '414'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '424'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '425'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '427'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '428'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '495'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0001',
    NULL,
    42,
    '512'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '405'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '410'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '414'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '424'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '425'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '427'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-0009',
    '2025-13271',
    42,
    '428'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '405'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '410'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '414'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '424'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '425'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '427'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14108',
    '2025-19787',
    42,
    '428'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '405'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '410'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '414'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '424'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '425'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '427'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-14109',
    '2025-21458',
    42,
    '428'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-1544',
    '2025-15492',
    42,
    '405'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-1544',
    '2025-15492',
    42,
    '410'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-1544',
    '2025-15492',
    42,
    '414'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-1544',
    '2025-15492',
    42,
    '424'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0304-1544',
    '2025-15492',
    42,
    '425'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0240-0001',
    '2025-20681',
    42,
    '413'
);

INSERT INTO cfrParts(
    document_id,
    frDocNum,
    title,
    cfrPart
) VALUES (
    'CMS-2025-0240-0001',
    '2025-20681',
    42,
    '512'
);