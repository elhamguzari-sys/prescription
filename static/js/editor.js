// static/prescription/js/editor.js

/**
 * ویرایشگر Canva-style برای دیزاین نسخه
 * - Drag & Drop
 * - Resize
 * - ذخیره خودکار
 * - آپلود عکس پس‌زمینه
 */

const Editor = (function() {
    'use strict';

    // ================================================================
    // State
    // ================================================================
    const state = {
        // تنظیمات دیزاین
        templateId: null,
        templateName: '',
        canvasWidth: 0,
        canvasHeight: 0,
        dpi: 300,

        // فیلدها
        fields: [],
        selectedId: null,
        nextTempId: 1,

        // UI
        zoom: 0.7,
        gridOn: false,
        snapOn: true,

        // Drag & Drop
        isDragging: false,
        dragEl: null,
        dragStart: { x: 0, y: 0 },
        dragOffset: { x: 0, y: 0 },

        // Resize
        isResizing: false,
        resizeHandle: null,
        resizeStart: { x: 0, y: 0, w: 0, h: 0 },
        resizeMouse: { x: 0, y: 0 },

        // History
        history: [],
        historyIndex: -1,

        // ذخیره
        isSaving: false,
        saveTimer: null,

        // URLs و CSRF
        urls: {},
        csrfToken: '',
    };


    // ================================================================
    // Initialize
    // ================================================================
    function init() {
        console.log('🎨 Editor initialized');

        const dataEl = document.getElementById('editorData');
        if (!dataEl) {
            console.error('❌ editorData not found');
            return;
        }

        const data = JSON.parse(dataEl.textContent);

        Object.assign(state, {
            templateId: data.templateId,
            templateName: data.templateName,
            canvasWidth: data.canvasWidth,
            canvasHeight: data.canvasHeight,
            dpi: data.dpi,
            fields: data.fields || [],
            urls: data.urls || {},
            csrfToken: data.csrfToken || '',
        });

        // شمارنده
        state.nextTempId = Math.max(
            1,
            ...state.fields.map(f => {
                if (typeof f.id === 'number') return f.id + 1;
                return 1;
            })
        );

        renderAllFields();
        updateZoomUI();
        updateFieldCount();
        updateSaveStatus('idle');
        setupEventListeners();
        startAutoSave();

        console.log(`✅ Loaded ${state.fields.length} fields`);
    }


    // ================================================================
    // Event Listeners
    // ================================================================
    function setupEventListeners() {
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('keydown', onKeyDown);

        const scrollArea = document.getElementById('canvasScrollArea');
        if (scrollArea) {
            scrollArea.addEventListener('wheel', onWheelZoom, { passive: false });
        }

        const nameInput = document.getElementById('templateName');
        if (nameInput) {
            nameInput.addEventListener('input', function() {
                state.templateName = this.value;
                scheduleAutoSave();
            });
        }

        // ✅ Drag & Drop برای عکس پس‌زمینه در مودال
        const uploadZone = document.getElementById('uploadZone');
        if (uploadZone) {
            ['dragenter', 'dragover'].forEach(evt => {
                uploadZone.addEventListener(evt, e => {
                    e.preventDefault();
                    uploadZone.classList.add('dragover');
                });
            });
            ['dragleave', 'drop'].forEach(evt => {
                uploadZone.addEventListener(evt, e => {
                    e.preventDefault();
                    uploadZone.classList.remove('dragover');
                });
            });
            uploadZone.addEventListener('drop', e => {
                const file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    const input = document.getElementById('id_new_background');
                    if (input) {
                        input.files = e.dataTransfer.files;
                        handleBackgroundSelect(input);
                    }
                }
            });
        }
    }


    // ================================================================
    // Render All Fields
    // ================================================================
    function renderAllFields() {
        const layer = document.getElementById('elementsLayer');
        if (!layer) return;

        layer.innerHTML = '';
        state.fields.forEach(field => renderField(field));
        updateSelectionUI();
    }


    function renderField(field) {
        const layer = document.getElementById('elementsLayer');
        if (!layer) return;

        const existing = document.getElementById(`field-${field.id}`);
        if (existing) existing.remove();

        const el = document.createElement('div');
        el.id = `field-${field.id}`;
        el.className = 'editor-element';
        el.dataset.fieldId = field.id;
        el.dataset.fieldType = field.field_type;
        el.style.position = 'absolute';
        el.style.left = field.x + 'px';
        el.style.top = field.y + 'px';
        el.style.width = field.width + 'px';
        el.style.fontFamily = `'${field.font_family || 'Vazirmatn'}', Tahoma, sans-serif`;
        el.style.fontSize = (field.font_size || 14) + 'px';
        el.style.fontWeight = field.font_weight === 'bold' ? 'bold' : 'normal';
        el.style.color = field.color || '#0f172a';
        el.style.textAlign = field.text_align || 'right';

        // ✅ سایه
        if (field.has_shadow) {
            el.style.textShadow = `2px 2px 4px ${field.shadow_color || '#000000'}`;
        }

        // ✅ خط دور (با text-stroke پشتیبانی نمی‌شود، از text-shadow استفاده می‌کنیم)
        if (field.has_stroke) {
            const strokeColor = field.stroke_color || '#ffffff';
            const sw = field.stroke_width || 1;
            const shadows = [];
            for (let dx = -sw; dx <= sw; dx++) {
                for (let dy = -sw; dy <= sw; dy++) {
                    if (dx === 0 && dy === 0) continue;
                    shadows.push(`${dx}px ${dy}px 0 ${strokeColor}`);
                }
            }
            el.style.textShadow = shadows.join(', ');
        }

        // متن
        el.textContent = getFieldPlaceholder(field);

        el.addEventListener('mousedown', onFieldMouseDown);
        el.addEventListener('click', function(e) {
            e.stopPropagation();
            selectField(field.id);
        });

        layer.appendChild(el);
    }


    function getFieldPlaceholder(field) {
        if (field.custom_text) return field.custom_text;
        if (field.label) return field.label;

        const placeholders = {
            'patient_name': 'نام بیمار',
            'patient_age': 'سن',
            'patient_gender': 'جنسیت',
            'patient_date': 'تاریخ',
            'patient_file': 'شماره پرونده',
            'vital_bp': 'BP',
            'vital_pr': 'PR',
            'vital_rr': 'RR',
            'vital_temp': 'Temp',
            'vital_spo2': 'Spo2',
            'vital_bs': 'BS',
            'vital_weight': 'وزن',
            'vital_height': 'قد',
            'vital_bmi': 'BMI',
            'chief_complaint': 'شکایت اصلی',
            'primary_diagnosis': 'تشخیص',
            'secondary_diagnoses': 'تشخیص‌های دیگر',
            'icd_code': 'ICD-10',
            'medical_history': 'سابقه بیماری',
            'surgical_history': 'سابقه جراحی',
            'family_history': 'سابقه فامیلی',
            'allergies': 'حساسیت',
            'current_medications': 'دواهای فعلی',
            'present_illness': 'شرح حال',
            'examination_findings': 'معاینه',
            'severity': 'شدت',
            'lab_tests': 'آزمایشات',
            'imaging': 'تصویربرداری',
            'procedures': 'اقدامات',
            'referral': 'ارجاع',
            'follow_up': 'پیگیری',
            'treatment_plan': 'توصیه',
            'doctor_note': 'یادداشت',
            'medications_list': '۱. دوا\n۲. دوا',
            'meds_dosage': '۱. دوز\n۲. دوز',
            'meds_frequency': '۱. دفعات\n۲. دفعات',
            'meds_duration': '۱. مدت\n۲. مدت',
            'doctor_name': 'نام داکتر',
            'doctor_specialization': 'تخصص',
        };
        return placeholders[field.field_type] || field.field_type;
    }


    // ================================================================
    // Add Field
    // ================================================================
    function addField(fieldType, label) {
        console.log('🎯 Add field:', fieldType, label);

        const id = 'temp_' + state.nextTempId++;

        const newField = {
            id: id,
            field_type: fieldType,
            label: label || '',
            custom_text: '',
            x: Math.round(state.canvasWidth / 4),
            y: Math.round(100 + state.fields.length * 40),
            width: 300,
            font_family: 'Vazirmatn',
            font_size: 20,
            font_weight: 'normal',
            color: '#0f172a',
            text_align: 'right',
            has_shadow: false,
            shadow_color: '#000000',
            has_stroke: false,
            stroke_color: '#ffffff',
            stroke_width: 1,
            order: state.fields.length,
            is_new: true,
        };

        state.fields.push(newField);
        renderField(newField);
        selectField(id);
        pushHistory();
        scheduleAutoSave();
        updateFieldCount();
        showToast(`«${label}» اضافه شد`, 'success');
    }


    // ================================================================
    // Select / Deselect
    // ================================================================
    function selectField(id) {
        state.selectedId = id;
        updateSelectionUI();
        showPropertiesForField(id);
    }


    function deselectAll(e) {
        if (e && e.target.closest('.editor-element')) return;

        state.selectedId = null;
        updateSelectionUI();
        hideProperties();
    }


    function updateSelectionUI() {
        document.querySelectorAll('.editor-element').forEach(el => {
            el.classList.toggle('selected', String(el.dataset.fieldId) === String(state.selectedId));
        });
        drawSelectionBox();
    }


    // ================================================================
    // Selection Box + Handles
    // ================================================================
    function drawSelectionBox() {
        const layer = document.getElementById('selectionLayer');
        if (!layer) return;

        layer.innerHTML = '';
        if (!state.selectedId) return;

        const el = document.getElementById(`field-${state.selectedId}`);
        if (!el) return;

        const box = document.createElement('div');
        box.className = 'selection-box';
        box.style.left = el.style.left;
        box.style.top = el.style.top;
        box.style.width = el.style.width;
        box.style.height = el.offsetHeight + 'px';

        const handles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
        handles.forEach(h => {
            const handle = document.createElement('div');
            handle.className = `selection-handle ${h}`;
            handle.addEventListener('mousedown', function(e) {
                startResize(e, h);
            });
            box.appendChild(handle);
        });

        layer.appendChild(box);
    }


    // ================================================================
    // Drag
    // ================================================================
    function onFieldMouseDown(e) {
        if (e.button !== 0) return;
        if (e.target.closest('.selection-handle')) return;

        const el = e.target.closest('.editor-element');
        if (!el) return;

        e.preventDefault();
        e.stopPropagation();

        const id = el.dataset.fieldId;
        selectField(id);

        state.isDragging = true;
        state.dragEl = el;
        state.dragStart = { x: e.clientX, y: e.clientY };

        const rect = el.getBoundingClientRect();
        state.dragOffset = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
        };

        el.classList.add('dragging');
    }


    function onMouseMove(e) {
        if (state.isResizing) {
            handleResize(e);
            return;
        }

        if (!state.isDragging || !state.dragEl) return;

        const canvasRect = document.getElementById('canvasPaper').getBoundingClientRect();

        let x = (e.clientX - canvasRect.left) / state.zoom - state.dragOffset.x / state.zoom;
        let y = (e.clientY - canvasRect.top) / state.zoom - state.dragOffset.y / state.zoom;

        if (state.snapOn) {
            x = Math.round(x / 5) * 5;
            y = Math.round(y / 5) * 5;
        }

        x = Math.max(0, Math.min(x, state.canvasWidth - 50));
        y = Math.max(0, Math.min(y, state.canvasHeight - 20));

        state.dragEl.style.left = Math.round(x) + 'px';
        state.dragEl.style.top = Math.round(y) + 'px';

        document.getElementById('propX').value = Math.round(x);
        document.getElementById('propY').value = Math.round(y);

        drawSelectionBox();
    }


    function onMouseUp() {
        if (state.isResizing) {
            state.isResizing = false;
            state.resizeHandle = null;
            pushHistory();
            scheduleAutoSave();
            return;
        }

        if (state.isDragging && state.dragEl) {
            const id = state.dragEl.dataset.fieldId;
            const field = state.fields.find(f => String(f.id) === String(id));

            if (field) {
                field.x = parseInt(state.dragEl.style.left);
                field.y = parseInt(state.dragEl.style.top);
            }

            state.dragEl.classList.remove('dragging');
            state.isDragging = false;
            state.dragEl = null;
            pushHistory();
            scheduleAutoSave();
        }
    }


    // ================================================================
    // Resize
    // ================================================================
    function startResize(e, handle) {
        e.preventDefault();
        e.stopPropagation();
        if (!state.selectedId) return;

        const el = document.getElementById(`field-${state.selectedId}`);
        if (!el) return;

        state.isResizing = true;
        state.resizeHandle = handle;
        state.resizeStart = {
            x: parseInt(el.style.left) || 0,
            y: parseInt(el.style.top) || 0,
            w: parseInt(el.style.width) || 100,
            h: el.offsetHeight,
        };
        state.resizeMouse = { x: e.clientX, y: e.clientY };
    }


    function handleResize(e) {
        if (!state.selectedId) return;

        const el = document.getElementById(`field-${state.selectedId}`);
        if (!el) return;

        const dx = (e.clientX - state.resizeMouse.x) / state.zoom;
        let { x, w } = state.resizeStart;
        const minW = 50;

        switch (state.resizeHandle) {
            case 'se': w = Math.max(minW, w + dx); break;
            case 'sw': w = Math.max(minW, w - dx); x = state.resizeStart.x + dx; break;
            case 'ne': w = Math.max(minW, w + dx); break;
            case 'nw': w = Math.max(minW, w - dx); x = state.resizeStart.x + dx; break;
            case 'e':  w = Math.max(minW, w + dx); break;
            case 'w':  w = Math.max(minW, w - dx); x = state.resizeStart.x + dx; break;
        }

        el.style.left = Math.round(x) + 'px';
        el.style.width = Math.round(w) + 'px';

        document.getElementById('propX').value = Math.round(x);
        document.getElementById('propWidth').value = Math.round(w);

        drawSelectionBox();
    }


    // ================================================================
    // Properties Panel
    // ================================================================
    function showPropertiesForField(id) {
        const field = state.fields.find(f => String(f.id) === String(id));
        if (!field) return;

        document.getElementById('propertiesEmpty').style.display = 'none';
        document.getElementById('propertiesContent').style.display = 'block';

        document.getElementById('propFieldType').textContent = field.label || field.field_type;
        document.getElementById('propFieldId').textContent = field.id;

        document.getElementById('propX').value = Math.round(field.x);
        document.getElementById('propY').value = Math.round(field.y);
        document.getElementById('propWidth').value = Math.round(field.width);
        document.getElementById('propOrder').value = field.order || 0;

        document.getElementById('propFontFamily').value = field.font_family || 'Vazirmatn';
        document.getElementById('propFontSize').value = field.font_size || 14;
        document.getElementById('propFontWeight').value = field.font_weight || 'normal';
        document.getElementById('propTextAlign').value = field.text_align || 'right';
        document.getElementById('propColor').value = field.color || '#0f172a';
        document.getElementById('propColorText').value = field.color || '#0f172a';

        document.getElementById('propCustomText').value = field.custom_text || '';
        document.getElementById('propLabel').value = field.label || '';

        // سایه
        document.getElementById('propHasShadow').checked = field.has_shadow || false;
        document.getElementById('propShadowColor').value = field.shadow_color || '#000000';
        document.getElementById('propShadowColorText').value = field.shadow_color || '#000000';
        document.getElementById('shadowColorGroup').style.display = field.has_shadow ? 'block' : 'none';

        // خط دور
        document.getElementById('propHasStroke').checked = field.has_stroke || false;
        document.getElementById('propStrokeColor').value = field.stroke_color || '#ffffff';
        document.getElementById('propStrokeColorText').value = field.stroke_color || '#ffffff';
        document.getElementById('propStrokeWidth').value = field.stroke_width || 1;
        document.getElementById('strokeColorGroup').style.display = field.has_stroke ? 'block' : 'none';
        document.getElementById('strokeWidthGroup').style.display = field.has_stroke ? 'block' : 'none';
    }


    function hideProperties() {
        document.getElementById('propertiesEmpty').style.display = 'flex';
        document.getElementById('propertiesContent').style.display = 'none';
    }


    // ================================================================
    // Update Properties
    // ================================================================
    function updateProp(key, value) {
        if (!state.selectedId) return;
        const field = state.fields.find(f => String(f.id) === String(state.selectedId));
        if (!field) return;

        if (['x', 'y', 'width', 'order'].includes(key)) {
            field[key] = parseInt(value) || 0;
            const el = document.getElementById(`field-${state.selectedId}`);
            if (el) {
                if (key === 'x') el.style.left = value + 'px';
                if (key === 'y') el.style.top = value + 'px';
                if (key === 'width') el.style.width = value + 'px';
            }
            drawSelectionBox();
        } else if (key === 'custom_text' || key === 'label') {
            field[key] = value;
            renderField(field);
            selectField(field.id);
        }

        scheduleAutoSave();
    }


    function updateStyle(key, value) {
        if (!state.selectedId) return;

        const field = state.fields.find(f => String(f.id) === String(state.selectedId));
        if (!field) return;

        field[key] = value;

        // نمایش/مخفی کردن گروه رنگ سایه
        if (key === 'has_shadow') {
            document.getElementById('shadowColorGroup').style.display = value ? 'block' : 'none';
        }
        // نمایش/مخفی کردن گروه خط دور
        if (key === 'has_stroke') {
            document.getElementById('strokeColorGroup').style.display = value ? 'block' : 'none';
            document.getElementById('strokeWidthGroup').style.display = value ? 'block' : 'none';
        }

        renderField(field);
        selectField(field.id);
        scheduleAutoSave();
    }


    // ================================================================
    // Delete / Duplicate
    // ================================================================
    function deleteSelected() {
        if (!state.selectedId) return;

        const field = state.fields.find(f => String(f.id) === String(state.selectedId));
        if (!field) return;

        if (!confirm(`حذف «${field.label || field.field_type}»؟`)) return;

        state.fields = state.fields.filter(f => String(f.id) !== String(state.selectedId));
        const el = document.getElementById(`field-${state.selectedId}`);
        if (el) el.remove();

        state.selectedId = null;
        updateSelectionUI();
        hideProperties();
        pushHistory();
        scheduleAutoSave();
        updateFieldCount();
        showToast('فیلد حذف شد', 'success');
    }


    function duplicateSelected() {
        if (!state.selectedId) return;

        const field = state.fields.find(f => String(f.id) === String(state.selectedId));
        if (!field) return;

        const clone = JSON.parse(JSON.stringify(field));
        clone.id = 'temp_' + state.nextTempId++;
        clone.x += 20;
        clone.y += 20;
        clone.is_new = true;

        state.fields.push(clone);
        renderField(clone);
        selectField(clone.id);
        pushHistory();
        scheduleAutoSave();
        updateFieldCount();
        showToast('فیلد کپی شد', 'success');
    }


    // ================================================================
    // Zoom
    // ================================================================
    function zoomIn() {
        state.zoom = Math.min(state.zoom + 0.1, 2.0);
        applyZoom();
    }


    function zoomOut() {
        state.zoom = Math.max(state.zoom - 0.1, 0.3);
        applyZoom();
    }


    function zoomReset() {
        state.zoom = 0.7;
        applyZoom();
    }


    function applyZoom() {
        const stage = document.getElementById('canvasStage');
        if (stage) stage.style.transform = `scale(${state.zoom})`;
        updateZoomUI();
    }


    function updateZoomUI() {
        const el = document.getElementById('zoomValue');
        if (el) el.textContent = Math.round(state.zoom * 100) + '%';
    }


    function onWheelZoom(e) {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (e.deltaY < 0) zoomIn();
            else zoomOut();
        }
    }


    // ================================================================
    // Grid / Snap
    // ================================================================
    function toggleGrid() {
        state.gridOn = !state.gridOn;
        const paper = document.getElementById('canvasPaper');
        if (paper) paper.classList.toggle('grid-on', state.gridOn);
    }


    function toggleSnap() {
        state.snapOn = !state.snapOn;
        showToast(state.snapOn ? 'چسبیدن فعال شد' : 'چسبیدن غیرفعال شد', 'info');
    }


    // ================================================================
    // Search
    // ================================================================
    function searchFields(query) {
        query = query.trim().toLowerCase();

        document.querySelectorAll('.field-item-card').forEach(card => {
            const label = (card.dataset.fieldLabel || '').toLowerCase();
            const type = (card.dataset.fieldType || '').toLowerCase();
            const match = !query || label.includes(query) || type.includes(query);
            card.classList.toggle('hidden', !match);
        });

        document.querySelectorAll('.field-category').forEach(cat => {
            const visible = cat.querySelectorAll('.field-item-card:not(.hidden)');
            cat.classList.toggle('hidden', visible.length === 0);
        });
    }


    // ================================================================
    // Update Field Count
    // ================================================================
    function updateFieldCount() {
        const el = document.getElementById('fieldCountLabel');
        if (el) {
            const count = state.fields.length;
            // تبدیل اعداد به فارسی
            const persianDigits = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
            const persianCount = String(count).split('').map(d => persianDigits[parseInt(d)]).join('');
            el.textContent = `${persianCount} فیلد`;
        }
    }


    // ================================================================
    // Background Upload
    // ================================================================
    function openBackgroundUpload() {
        const modal = new bootstrap.Modal(document.getElementById('uploadBackgroundModal'));
        modal.show();

        // ریست
        document.getElementById('backgroundPreview').style.display = 'none';
        document.getElementById('id_new_background').value = '';
        document.getElementById('uploadBackgroundBtn').disabled = true;
    }


    function handleBackgroundSelect(input) {
        const file = input.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('لطفاً فقط فایل تصویری انتخاب کنید.');
            return;
        }

        if (file.size > 20 * 1024 * 1024) {
            alert('حجم فایل نباید بیشتر از ۲۰ مگابایت باشد.');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('backgroundPreviewImg').src = e.target.result;
            document.getElementById('backgroundFilename').textContent = file.name;
            document.getElementById('backgroundPreview').style.display = 'block';
            document.getElementById('uploadBackgroundBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }


    function uploadBackground() {
        const input = document.getElementById('id_new_background');
        if (!input.files[0]) return;

        const formData = new FormData();
        formData.append('background_image', input.files[0]);

        const btn = document.getElementById('uploadBackgroundBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> در حال آپلود...';

        fetch(state.urls.uploadBackground, {
            method: 'POST',
            headers: {
                'X-CSRFToken': state.csrfToken,
            },
            body: formData,
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast('عکس پس‌زمینه آپلود شد', 'success');
                // رفرش برای اعمال عکس جدید
                setTimeout(() => location.reload(), 800);
            } else {
                throw new Error(data.error || 'خطای آپلود');
            }
        })
        .catch(err => {
            console.error('Upload error:', err);
            showToast('خطا: ' + err.message, 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-lg"></i> آپلود';
        });
    }


    // ================================================================
    // History (Undo/Redo)
    // ================================================================
    function pushHistory() {
        const snapshot = JSON.stringify(state.fields);
        state.history = state.history.slice(0, state.historyIndex + 1);
        state.history.push(snapshot);
        if (state.history.length > 50) state.history.shift();
        state.historyIndex = state.history.length - 1;
    }


    function undo() {
        if (state.historyIndex <= 0) return;
        state.historyIndex--;
        state.fields = JSON.parse(state.history[state.historyIndex]);
        renderAllFields();
        state.selectedId = null;
        hideProperties();
        updateFieldCount();
        scheduleAutoSave();
    }


    function redo() {
        if (state.historyIndex >= state.history.length - 1) return;
        state.historyIndex++;
        state.fields = JSON.parse(state.history[state.historyIndex]);
        renderAllFields();
        state.selectedId = null;
        hideProperties();
        updateFieldCount();
        scheduleAutoSave();
    }


    // ================================================================
    // Keyboard
    // ================================================================
    function onKeyDown(e) {
        // Ctrl+S
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            save();
            return;
        }

        // Ctrl+Z
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undo();
            return;
        }

        // Ctrl+Y
        if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
            e.preventDefault();
            redo();
            return;
        }

        // Delete
        if ((e.key === 'Delete' || e.key === 'Backspace') && state.selectedId) {
            const tag = document.activeElement.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
            e.preventDefault();
            deleteSelected();
            return;
        }

        // Escape
        if (e.key === 'Escape') {
            deselectAll();
            return;
        }

        // Arrows
        if (state.selectedId && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            const tag = document.activeElement.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

            e.preventDefault();
            const field = state.fields.find(f => String(f.id) === String(state.selectedId));
            if (!field) return;

            const step = e.shiftKey ? 10 : 1;
            if (e.key === 'ArrowUp') field.y -= step;
            if (e.key === 'ArrowDown') field.y += step;
            if (e.key === 'ArrowLeft') field.x -= step;
            if (e.key === 'ArrowRight') field.x += step;

            field.x = Math.max(0, field.x);
            field.y = Math.max(0, field.y);

            const el = document.getElementById(`field-${field.id}`);
            if (el) {
                el.style.left = field.x + 'px';
                el.style.top = field.y + 'px';
            }
            document.getElementById('propX').value = field.x;
            document.getElementById('propY').value = field.y;
            drawSelectionBox();
            scheduleAutoSave();
        }
    }


    // ================================================================
    // Save
    // ================================================================
    function save() {
        if (state.isSaving) return;

        state.isSaving = true;
        updateSaveStatus('saving');

        const nameInput = document.getElementById('templateName');
        if (nameInput) state.templateName = nameInput.value;

        const payload = {
            name: state.templateName,
            fields: state.fields.map(f => ({
                id: String(f.id).startsWith('temp_') ? null : f.id,
                field_type: f.field_type,
                label: f.label || '',
                custom_text: f.custom_text || '',
                x: parseInt(f.x) || 0,
                y: parseInt(f.y) || 0,
                width: parseInt(f.width) || 300,
                font_family: f.font_family || 'Vazirmatn',
                font_size: parseInt(f.font_size) || 14,
                font_weight: f.font_weight || 'normal',
                color: f.color || '#0f172a',
                text_align: f.text_align || 'right',
                has_shadow: !!f.has_shadow,
                shadow_color: f.shadow_color || '#000000',
                has_stroke: !!f.has_stroke,
                stroke_color: f.stroke_color || '#ffffff',
                stroke_width: parseInt(f.stroke_width) || 1,
                order: f.order || 0,
            })),
        };

        fetch(state.urls.saveFields, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken,
            },
            body: JSON.stringify(payload),
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateSaveStatus('saved');
                showToast('ذخیره شد', 'success');

                if (state.fields.some(f => String(f.id).startsWith('temp_'))) {
                    setTimeout(() => location.reload(), 800);
                }
            } else {
                throw new Error(data.error || 'خطای ذخیره');
            }
        })
        .catch(err => {
            console.error('Save error:', err);
            updateSaveStatus('error');
            showToast('خطا: ' + err.message, 'error');
        })
        .finally(() => {
            state.isSaving = false;
        });
    }


    function scheduleAutoSave() {
        if (state.saveTimer) clearTimeout(state.saveTimer);
        state.saveTimer = setTimeout(save, 5000);
    }


    function startAutoSave() {
        setInterval(() => {
            if (!state.isSaving && state.fields.length > 0) save();
        }, 120000);
    }


    function updateSaveStatus(status) {
        const el = document.getElementById('saveStatus');
        if (!el) return;

        el.classList.remove('saved', 'saving', 'error');

        const icons = {
            'idle':    '<i class="bi bi-cloud"></i> آماده',
            'saving':  '<i class="bi bi-cloud-arrow-up"></i> در حال ذخیره...',
            'saved':   '<i class="bi bi-cloud-check"></i> ذخیره شد',
            'error':   '<i class="bi bi-cloud-slash"></i> خطا',
        };

        el.innerHTML = icons[status] || icons.idle;
        if (status !== 'idle') el.classList.add(status);
    }


    // ================================================================
    // Toast
    // ================================================================
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast-item ${type}`;

        const icons = {
            success: 'bi-check-circle-fill',
            error:   'bi-x-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info:    'bi-info-circle-fill',
        };

        toast.innerHTML = `<i class="bi ${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }


    // ================================================================
    // Toggle Sidebars (for mobile)
    // ================================================================
    function togglePropertiesSidebar() {
        const sidebar = document.getElementById('propertiesSidebar');
        if (sidebar) sidebar.classList.toggle('open');
    }


    function toggleFieldsSidebar() {
        const sidebar = document.getElementById('fieldsSidebar');
        if (sidebar) sidebar.classList.toggle('open');
    }


    // ================================================================
    // Public API
    // ================================================================
    return {
        init,
        addField,
        deleteSelected,
        duplicateSelected,
        selectField,
        deselectAll,
        updateProp,
        updateStyle,
        save,
        undo,
        redo,
        zoomIn,
        zoomOut,
        zoomReset,
        toggleGrid,
        toggleSnap,
        searchFields,
        openBackgroundUpload,
        handleBackgroundSelect,
        uploadBackground,
        togglePropertiesSidebar,
        toggleFieldsSidebar,
        showToast,
        state,
    };
})();


// ================================================================
// Auto-init
// ================================================================
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('editorContainer')) {
        Editor.init();
    }
});