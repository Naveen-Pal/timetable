document.addEventListener('DOMContentLoaded', function() {
    let selectedCourses = [];
    let courseData = [];
    let totalCredits = 0;
    let timetableData = null;
    
    // DOM elements
    const $ = id => document.getElementById(id);
    const elements = {
        searchField: $('search-field'),
        courseTableBody: $('course-table-body'),
        previewButton: $('preview-button'),
        deselectAllButton: $('deselect-all'),
        timetableContainer: $('timetable-container'),
        downloadOptions: $('download-options'),
        downloadImage: $('download-image'),
        downloadExcel: $('download-excel'),
        downloadCSV: $('download-csv'),
        downloadICS: $('download-ics'),
        totalCreditsElement: $('total-credits'),
        errorBox: $('error-box'),
        successBox: $('success-box'),
        selectedCoursesContainer: $('selected-courses-container'),
        selectedCoursesList: $('selected-courses-list')
    };
    
    // Initialize
    loadCourses();
    setupEventListeners();
    
    // Load courses from API
    function loadCourses() {
        fetch('/api/courses')
            .then(response => response.json())
            .then(data => {
                courseData = data.courses;
                renderCourseTable();
            })
            .catch(() => showMessage('Failed to load course data. Please refresh.', 'error'));
    }
    
    // Setup all event listeners
    function setupEventListeners() {
        elements.searchField.addEventListener('input', e => renderCourseTable(e.target.value.toLowerCase()));
        elements.previewButton.addEventListener('click', () => validateAndGenerate(generateTimetable));
        elements.deselectAllButton.addEventListener('click', deselectAll);
        
        // Go to top button
        $('go-to-top').addEventListener('click', scrollToTop);
        
        // Download handlers
        ['Image', 'Excel', 'CSV', 'ICS'].forEach(type => {
            $(`download-${type.toLowerCase()}`).addEventListener('click', () => 
                validateAndGenerate(() => window[`generateTimetable${type}`]())
            );
        });
    }
    
    // Render course table with optional search filter
    function renderCourseTable(searchQuery = '') {
        const tbody = elements.courseTableBody;
        const filteredCourses = courseData.filter(course => 
            course.code.toLowerCase().includes(searchQuery) || 
            course.name.toLowerCase().includes(searchQuery)
        );
        
        if (filteredCourses.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No courses found.</td></tr>';
            return;
        }
        
        tbody.innerHTML = filteredCourses.map(course => `
            <tr>
                <td>${course.code}</td>
                <td>${course.name}</td>
                <td>${course.credits}</td>
                <td>
                    <div class="course-checkbox-wrapper">
                        <input type="checkbox" ${selectedCourses.includes(course.code) ? 'checked' : ''} 
                               data-course-code="${course.code}" data-credits="${course.credits}">
                    </div>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners to checkboxes
        tbody.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', handleCourseSelection);
        });
    }
    
    // Handle course selection/deselection
    function handleCourseSelection(e) {
        const { courseCode, credits } = e.target.dataset;
        const creditsNum = parseInt(credits);
        
        if (e.target.checked) {
            if (!selectedCourses.includes(courseCode)) {
                selectedCourses.push(courseCode);
                totalCredits += creditsNum;
            }
        } else {
            const index = selectedCourses.indexOf(courseCode);
            if (index > -1) {
                selectedCourses.splice(index, 1);
                totalCredits -= creditsNum;
            }
        }
        
        updateTotalCredits();
        updateSelectedCourses();
    }
    
    // Update total credits display
    function updateTotalCredits() {
        elements.totalCreditsElement.textContent = totalCredits;
    }
    
    // Update selected courses display
    function updateSelectedCourses() {
        if (selectedCourses.length === 0) {
            elements.selectedCoursesContainer.style.display = 'none';
            return;
        }
        
        elements.selectedCoursesList.innerHTML = selectedCourses.map(courseCode => {
            const course = courseData.find(c => c.code === courseCode);
            return course ? `
                <div class="selected-course-item">
                    <span class="selected-course-code">${course.code}</span>
                    <span class="selected-course-name">${course.name}</span>
                    <span class="selected-course-credits">${course.credits}C</span>
                    <button class="remove-course-btn" onclick="removeCourse('${course.code}', ${course.credits})" title="Remove course">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            ` : '';
        }).join('');
        
        elements.selectedCoursesContainer.style.display = 'block';
    }
    
    // Remove individual course (global function for onclick)
    window.removeCourse = function(courseCode, credits) {
        const index = selectedCourses.indexOf(courseCode);
        if (index > -1) {
            selectedCourses.splice(index, 1);
            totalCredits -= credits;
            updateTotalCredits();
            renderCourseTable(elements.searchField.value.toLowerCase());
            updateSelectedCourses();
            showMessage(`${courseCode} removed from selection.`, 'success');
        }
    };
    
    // Deselect all courses
    function deselectAll() {
        selectedCourses = [];
        totalCredits = 0;
        updateTotalCredits();
        renderCourseTable(elements.searchField.value.toLowerCase());
        elements.timetableContainer.innerHTML = '';
        elements.downloadOptions.style.display = 'none';
        elements.selectedCoursesContainer.style.display = 'none';
        showMessage('All courses deselected.', 'success');
    }
    
    // Validate selection and execute callback
    function validateAndGenerate(callback) {
        if (selectedCourses.length === 0) {
            showMessage('Please select at least one course.', 'error');
            return;
        }
        callback();
    }
    
    // Generate timetable
    function generateTimetable() {
        updateSelectedCourses();
        elements.timetableContainer.innerHTML = '<div class="loader" style="display:block;"></div>';
        
        fetch('/api/timetable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ courses: selectedCourses })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showMessage(data.error, 'error');
                return;
            }
            
            timetableData = data;
            renderTimetable(data);
            elements.downloadOptions.style.display = 'flex';
            scrollToTop();
        })
        .catch(() => {
            showMessage('Failed to generate timetable.', 'error');
            elements.timetableContainer.innerHTML = '';
        });
    }
    
    // Render timetable HTML
    function renderTimetable(data) {
        const timeSlots = [...new Set(Object.values(data).flat().map(entry => entry.time))]
            .sort((a, b) => parseInt(a.split(':')[0]) - parseInt(b.split(':')[0]));
        
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
        const dayKeys = days.map(day => day.toLowerCase());
        
        const table = `
            <table class="timetable">
                <thead>
                    <tr>
                        <th>Time</th>
                        ${days.map(day => `<th>${day}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${timeSlots.map(timeSlot => `
                        <tr>
                            <td class="time-slot">${timeSlot}</td>
                            ${dayKeys.map(dayKey => {
                                const courseEntry = (data[dayKey] || []).find(entry => entry.time === timeSlot);
                                return `<td>${courseEntry ? formatCourseCell(courseEntry.class) : ''}</td>`;
                            }).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        elements.timetableContainer.innerHTML = table;
    }
    
    // Format course cell content
    function formatCourseCell(classInfo) {
        const parts = classInfo.split(',').map(part => part.trim());
        const spans = ['course-code', 'course-name', 'course-type', 'course-location'];
        
        return `<div class="course-cell">
            ${parts.map((part, i) => part ? `<span class="${spans[i] || ''}">${part}</span>` : '').join('')}
        </div>`;
    }
    
    // Download functions
    window.generateTimetableImage = function() {
        const table = elements.timetableContainer.querySelector('.timetable');
        if (!table) return showMessage('Generate timetable first.', 'error');
        
        showMessage('Generating image...', 'success');
        html2canvas(table, { backgroundColor: '#ffffff', scale: 2 })
            .then(canvas => downloadFile(canvas.toDataURL('image/png'), 'png'))
            .catch(() => showMessage('Failed to generate image.', 'error'));
    };
    
    window.generateTimetableExcel = function() {
        if (!timetableData) return showMessage('Generate timetable first.', 'error');
        
        const data = formatTableData();
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(data);
        XLSX.utils.book_append_sheet(wb, ws, "Timetable");
        XLSX.writeFile(wb, `Timetable_${getTimestamp()}.xlsx`);
        showMessage('Excel downloaded!', 'success');
    };
    
    window.generateTimetableCSV = function() {
        if (!timetableData) return showMessage('Generate timetable first.', 'error');
        
        const data = formatTableData();
        const csv = data.map(row => row.map(cell => 
            cell.includes(',') ? `"${cell}"` : cell
        ).join(',')).join('\n');
        
        downloadFile(`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`, 'csv');
        showMessage('CSV downloaded!', 'success');
    };
    
    window.generateTimetableICS = function() {
        if (!timetableData) return showMessage('Generate timetable first.', 'error');
        
        showMessage('Generating calendar file...', 'success');
        
        fetch('/api/download-ics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ courses: selectedCourses })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to generate ICS file');
            }
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `Timetable_${getTimestamp()}.ics`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            showMessage('Calendar file downloaded! Import it to your calendar app.', 'success');
        })
        .catch(() => {
            showMessage('Failed to generate calendar file.', 'error');
        });
    };
    
    // Helper functions
    function formatTableData() {
        const timeSlots = [...new Set(Object.values(timetableData).flat().map(entry => entry.time))]
            .sort((a, b) => parseInt(a.split(':')[0]) - parseInt(b.split(':')[0]));
        
        const header = ['Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
        const rows = timeSlots.map(timeSlot => {
            const row = [timeSlot];
            ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].forEach(day => {
                const course = (timetableData[day] || []).find(entry => entry.time === timeSlot);
                row.push(course ? course.class : '');
            });
            return row;
        });
        
        return [header, ...rows];
    }
    
    function downloadFile(url, extension) {
        const link = document.createElement('a');
        link.href = url;
        link.download = `Timetable_${getTimestamp()}.${extension}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        if (url.startsWith('blob:')) URL.revokeObjectURL(url);
    }
    
    function getTimestamp() {
        const now = new Date();
        return [now.getFullYear(), now.getMonth() + 1, now.getDate()]
            .map(n => n.toString().padStart(2, '0')).join('') + '_' +
            [now.getHours(), now.getMinutes(), now.getSeconds()]
            .map(n => n.toString().padStart(2, '0')).join('');
    }
    
    function showMessage(message, type) {
        const box = type === 'error' ? elements.errorBox : elements.successBox;
        const otherBox = type === 'error' ? elements.successBox : elements.errorBox;
        
        box.textContent = message;
        box.style.display = 'block';
        otherBox.style.display = 'none';
        setTimeout(() => box.style.display = 'none', 5000);
    }
    
    // Scroll to top function
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
});
