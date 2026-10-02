from flask import Flask, render_template_string, request, redirect, url_for, session
from datetime import datetime, timedelta
import calendar
import os
import json

app = Flask(__name__)
app.secret_key = 'brother_secret_key_change_this'

# [초기 오빠 비밀번호 설정] 패널 안에서 언제든 변경 가능합니다!
ADMIN_PASSWORD = "1234" 

# 데이터 저장을 위한 JSON 파일 경로
DATA_FILE = "checklist_data.json"

def load_data():
    """서버에 저장된 체크리스트 기록을 불러옵니다."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    """체크리스트 기록을 파일에 안전하게 저장합니다."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 1. 매일 해야 하는 일 목록
DAILY_TASKS = [
    {"id": 1, "task": "목욕버튼 끄기"},
    {"id": 2, "task": "문쪽 튄 물 닦기"},
    {"id": 3, "task": "샴푸통 같은 거 쓰러진거 세우기"}
]

# 2. 일요일 주간 청소 및 빨래 목록
WEEKLY_TASKS = [
    {"id": 101, "task": "화장실 전체 청소 및 소독 (변기, 세면대, 바닥)"},
    {"id": 102, "task": "거울 물때 제거 및 배수구 머리카락 치우기"},
    {"id": 103, "task": "빨래 널기"}
]

@app.route('/')
def index():
    today_str = datetime.now().strftime('%Y-%m-%d')
    current_date = request.args.get('date', today_str)
    is_today = (current_date == today_str)

    date_obj = datetime.strptime(current_date, '%Y-%m-%d')
    is_sunday = (date_obj.weekday() == 6)
    
    checklist_status = load_data()
    completed_today = checklist_status.get(current_date, [])
    
    return render_template_string(INDEX_TEMPLATE, 
                                  daily_tasks=DAILY_TASKS,
                                  weekly_tasks=WEEKLY_TASKS,
                                  completed_today=completed_today,
                                  current_date=current_date,
                                  today_str=today_str,
                                  is_sunday=is_sunday,
                                  is_today=is_today)

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    today_str = datetime.now().strftime('%Y-%m-%d')
    date = request.form.get('date', today_str)
    
    if not session.get('is_admin') and date != today_str:
        return redirect(url_for('index', date=today_str))

    checklist_status = load_data()

    if date not in checklist_status:
        checklist_status[date] = []
        
    if task_id in checklist_status[date]:
        checklist_status[date].remove(task_id)
    else:
        checklist_status[date].append(task_id)
        
    save_data(checklist_status)
    
    if request.form.get('from_admin') == 'true':
        return redirect(url_for('admin_panel'))
        
    return redirect(url_for('index', date=date))

@app.route('/calendar')
def calendar_page():
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    now = datetime.now()
    year = request.args.get('year', type=int, default=now.year)
    month = request.args.get('month', type=int, default=now.month)
    
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)
    
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
        
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    checklist_status = load_data()

    calendar_matrix = []
    for week in month_days:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(None)
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime(year, month, day)
                is_sun = (date_obj.weekday() == 6)
                
                tasks_for_day = [t['task'] for t in DAILY_TASKS]
                if is_sun:
                    tasks_for_day.extend([t['task'] for t in WEEKLY_TASKS])
                
                total_count = len(tasks_for_day)
                done_list = checklist_status.get(date_str, [])
                
                valid_weekly_ids = {t['id'] for t in WEEKLY_TASKS}
                done_count = sum(1 for tid in done_list if is_sun or tid not in valid_weekly_ids)
                
                is_completed = (done_count >= total_count and total_count > 0)
                is_past_day = (date_str < today_str)
                
                week_row.append({
                    "day": day,
                    "date": date_str,
                    "is_today": (date_str == today_str),
                    "is_sunday": is_sun,
                    "tasks": tasks_for_day,
                    "done_count": done_count,
                    "total_count": total_count,
                    "is_completed": is_completed,
                    "is_missed": (is_past_day and not is_completed)
                })
        calendar_matrix.append(week_row)

    return render_template_string(CALENDAR_TEMPLATE, 
                                  year=year, 
                                  month=month, 
                                  calendar_matrix=calendar_matrix,
                                  prev_year=prev_year, prev_month=prev_month,
                                  next_year=next_year, next_month=next_month)

@app.route('/secret-login', methods=['GET', 'POST'])
def secret_login():
    error = None
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = "비밀번호가 틀렸습니다!"
    return render_template_string(SECRET_LOGIN_TEMPLATE, error=error)

@app.route('/admin-panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('secret_login'))
    
    global ADMIN_PASSWORD
    success_msg = None
    error_msg = None

    if request.method == 'POST':
        current_pw = request.form.get('current_pw')
        new_pw = request.form.get('new_pw')
        confirm_pw = request.form.get('confirm_pw')

        if current_pw != ADMIN_PASSWORD:
            error_msg = "현재 비밀번호가 일치하지 않습니다."
        elif not new_pw:
            error_msg = "새 비밀번호를 입력해주세요."
        elif new_pw != confirm_pw:
            error_msg = "새 비밀번호가 서로 일치하지 않습니다."
        else:
            ADMIN_PASSWORD = new_pw
            success_msg = "비밀번호가 성공적으로 변경되었습니다!"

    now = datetime.now()
    history_logs = []
    total_completed_days = 0
    
    checklist_status = load_data()

    for i in range(14):
        target_date = now - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        is_sun = (target_date.weekday() == 6)
        
        tasks_for_day_def = list(DAILY_TASKS)
        if is_sun:
            tasks_for_day_def.extend(WEEKLY_TASKS)
            
        total_count = len(tasks_for_day_def)
        done_list = checklist_status.get(date_str, [])
        
        valid_weekly_ids = {t['id'] for t in WEEKLY_TASKS}
        done_count = sum(1 for tid in done_list if is_sun or tid not in valid_weekly_ids)
        
        is_completed = (done_count >= total_count and total_count > 0)
        if is_completed:
            total_completed_days += 1
            
        task_details = []
        for t_def in tasks_for_day_def:
            task_details.append({
                "id": t_def['id'],
                "task": t_def['task'],
                "done": t_def['id'] in done_list
            })

        history_logs.append({
            "date": date_str,
            "display": target_date.strftime('%m월 %d일 (%a)'),
            "done_count": done_count,
            "total_count": total_count,
            "is_completed": is_completed,
            "task_details": task_details
        })

    return render_template_string(ADMIN_PANEL_TEMPLATE, 
                                  history_logs=history_logs, 
                                  total_completed_days=total_completed_days,
                                  success_msg=success_msg,
                                  error_msg=error_msg)

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))


# 통합 스타일 및 템플릿
NAV_STYLE = '''
    <div class="nav-bar">
        <a href="/" class="nav-btn {% if request.path == '/' %}active{% endif %}">📋 오늘의 체크리스트</a>
        <a href="/calendar" class="nav-btn {% if request.path == '/calendar' %}active{% endif %}">🗓 월간 달력보기</a>
    </div>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f0f4f8; margin: 0; padding: 15px; color: #333; }
        .container { max-width: 650px; width: 100%; margin: auto; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); position: relative; }
        
        /* 캘린더 전용 와이드 컨테이너 (여백 최소화 & 화면 넓게 활용) */
        .container-wide { max-width: 1400px; width: 96%; margin: auto; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); position: relative; }

        h1 { font-size: 1.5em; color: #2c3e50; text-align: center; margin-bottom: 10px; font-weight: 800; }
        h2 { font-size: 1.1em; color: #2c3e50; margin-bottom: 10px; font-weight: 700; }
        
        .nav-bar { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #edf2f7; padding-bottom: 12px; }
        .nav-btn { text-decoration: none; padding: 10px; border-radius: 8px; background: #eef2f7; color: #64748b; font-weight: bold; font-size: 0.9em; transition: 0.2s; flex: 1; text-align: center; }
        .nav-btn.active { background: #3b82f6; color: white; box-shadow: 0 2px 5px rgba(59,130,246,0.3); }
        
        .date-selector { background: #f8fafc; padding: 10px 15px; border-radius: 10px; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 12px; border: 1px solid #e2e8f0; }
        
        ul { list-style: none; padding: 0; margin: 0; }
        li { background: #ffffff; margin: 10px 0; padding: 14px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .done { text-decoration: line-through; color: #94a3b8; }
        
        button { background: #3b82f6; color: white; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.85em; flex-shrink: 0; margin-left: 10px; transition: 0.2s; }
        button:hover { background: #2563eb; }
        button.disabled { background: #cbd5e1; cursor: not-allowed; }
        
        .today-btn { background: #10b981; padding: 5px 10px; font-size: 0.8em; text-decoration: none; color: white; border-radius: 6px; font-weight: bold; }
        .today-btn:hover { background: #059669; }
        
        .section-box { margin-top: 20px; background: #fff; border: 1px solid #e2e8f0; padding: 18px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .weekly-title { color: #8b5cf6; }
        .task-text { font-size: 0.95em; font-weight: 500; word-break: keep-all; line-height: 1.4; color: #1e293b; }
        
        /* 캘린더 스타일 대폭 확대 및 시원한 가독성 확보 */
        .calendar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; font-weight: bold; font-size: 1.3em; color: #1e293b; }
        .calendar-header a { text-decoration: none; background: #f1f5f9; padding: 8px 18px; border-radius: 8px; color: #475569; font-size: 0.85em; }
        .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .cal-table th { padding: 14px 0; font-size: 1em; color: #64748b; background: #f8fafc; border: 1px solid #e2e8f0; }
        .cal-table th:first-child { color: #ef4444; } 
        .cal-table th:last-child { color: #3b82f6; }  
        .cal-table td { height: 185px; border: 1px solid #e2e8f0; vertical-align: top; padding: 10px; text-align: left; background: #fff; overflow: hidden; transition: 0.15s; }
        .cal-table td:hover { background: #f1f5f9; }
        
        .cal-day-num { font-size: 1em; font-weight: bold; display: inline-block; margin-bottom: 6px; padding: 2px 7px; border-radius: 4px; }
        .cal-today { background: #eff6ff !important; border: 2px solid #3b82f6 !important; }
        
        .cal-done-cell { background: #ecfdf5 !important; border: 2px solid #10b981 !important; }
        .cal-missed-cell { background: #fef2f2 !important; border: 2px solid #ef4444 !important; }

        .task-chip { background: #f1f5f9; font-size: 0.8em; padding: 4px 8px; border-radius: 6px; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; color: #334155; font-weight: 500; }
        .task-chip.sunday-task { background: #f3e8ff; color: #7c3aed; }
        
        .status-badge { font-size: 0.75em; padding: 5px 6px; border-radius: 6px; display: block; margin-top: 8px; font-weight: bold; text-align: center; width: 100%; }
        .badge-done { background: #10b981; color: white; }
        .badge-missed { background: #ef4444; color: white; }
        .badge-ongoing { background: #f59e0b; color: white; }

        .secret-footer { margin-top: 30px; text-align: center; font-size: 0.8em; border-top: 1px dashed #cbd5e1; padding-top: 15px; }
        .secret-footer a { color: #94a3b8; text-decoration: none; font-weight: 500; }
        .secret-footer a:hover { color: #64748b; }
    </style>
'''

SECRET_FOOTER_HTML = '''
    <div class="secret-footer">
        <a href="/secret-login">🔒 오빠 전용 비밀 패널</a>
    </div>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>채린이의 스마트 청소 홈</title>
    ''' + NAV_STYLE + '''
</head>
<body>
    <div class="container">
        <h1>✨ 채린이의 청소 홈</h1>
        
        <div class="date-selector">
            <span style="font-weight: 700; font-size: 0.9em; color: #475569;">📅 오늘 날짜:</span>
            <span style="font-size: 1em; font-weight: 800; color: #1e293b;">{{ current_date }}</span>
            {% if not is_today %}
                <a href="/" class="today-btn">오늘로 돌아가기</a>
            {% endif %}
        </div>

        {% if not is_today %}
        <div style="background: #fef2f2; color: #991b1b; padding: 12px; border-radius: 8px; font-size: 0.85em; text-align: center; margin-bottom: 15px; border: 1px solid #fecaca; font-weight: 500;">
            ⚠️ 과거/미래 날짜는 **조회만** 가능하며 체크/취소는 오늘만 가능합니다!
        </div>
        {% endif %}

        <div class="section-box" style="margin-top:0;">
            <h2>🔄 매일 해야 할 일</h2>
            <ul>
                {% for item in daily_tasks %}
                <li>
                    <form action="/toggle_task/{{ item.id }}" method="post" style="display:flex; justify-content: space-between; align-items: center; width: 100%;">
                        <input type="hidden" name="date" value="{{ current_date }}">
                        <span class="task-text {% if item.id in completed_today %}done{% endif %}">
                            {% if item.id in completed_today %}✅{% else %}⬜{% endif %} {{ item.task }}
                        </span>
                        {% if is_today %}
                            <button type="submit">{% if item.id in completed_today %}취소{% else %}완료{% endif %}</button>
                        {% else %}
                            <button type="button" class="disabled" disabled>수정불가</button>
                        {% endif %}
                    </form>
                </li>
                {% endfor %}
            </ul>
        </div>

        {% if is_sunday %}
        <div class="section-box">
            <h2 class="weekly-title">🧹 일요일 주간 청소 및 빨래</h2>
            <p style="font-size: 0.85em; color: #7c3aed; margin-bottom: 12px; font-weight: 500;">오늘은 일요일! 한 주 동안 밀린 청소와 빨래를 깔끔하게 마무리해 보세요.</p>
            <ul>
                {% for item in weekly_tasks %}
                <li>
                    <form action="/toggle_task/{{ item.id }}" method="post" style="display:flex; justify-content: space-between; align-items: center; width: 100%;">
                        <input type="hidden" name="date" value="{{ current_date }}">
                        <span class="task-text {% if item.id in completed_today %}done{% endif %}">
                            {% if item.id in completed_today %}✅{% else %}⬜{% endif %} {{ item.task }}
                        </span>
                        {% if is_today %}
                            <button type="submit">{% if item.id in completed_today %}취소{% else %}완료{% endif %}</button>
                        {% else %}
                            <button type="button" class="disabled" disabled>수정불가</button>
                        {% endif %}
                    </form>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        ''' + SECRET_FOOTER_HTML + '''
    </div>
</body>
</html>
'''

CALENDAR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>채린이의 월간 달력보기</title>
    ''' + NAV_STYLE + '''
</head>
<body>
    <div class="container-wide">
        <h1>🗓️ 월간 달력 현황</h1>
        
        <div class="calendar-header">
            <a href="/calendar?year={{ prev_year }}&month={{ prev_month }}">◀ 이전</a>
            <span>{{ year }}년 {{ month }}월</span>
            <a href="/calendar?year={{ next_year }}&month={{ next_month }}">다음 ▶</a>
        </div>

        <table class="cal-table">
            <thead>
                <tr>
                    <th>일</th>
                    <th>월</th>
                    <th>화</th>
                    <th>수</th>
                    <th>목</th>
                    <th>금</th>
                    <th>토</th>
                </tr>
            </thead>
            <tbody>
                {% for week in calendar_matrix %}
                <tr>
                    {% for day_info in week %}
                        {% if day_info is none %}
                            <td style="background: #fafafa;"></td>
                        {% else %}
                            <td class="{% if day_info.is_today %}cal-today{% endif %} {% if day_info.is_completed %}cal-done-cell{% elif day_info.is_missed %}cal-missed-cell{% endif %}" onclick="location.href='/?date={{ day_info.date }}'" style="cursor: pointer;">
                                <span class="cal-day-num" style="{% if day_info.is_sunday %}color: #ef4444;{% elif loop.last %}color: #3b82f6;{% endif %}">{{ day_info.day }}</span>
                                
                                <div style="margin-top: 5px;">
                                    {% for task in day_info.tasks %}
                                        <span class="task-chip {% if '화장실' in task or '거울' in task or '빨래' in task %}sunday-task{% endif %}" title="{{ task }}">· {{ task }}</span>
                                    {% endfor %}
                                </div>

                                {% if day_info.total_count > 0 %}
                                    {% if day_info.is_completed %}
                                        <span class="status-badge badge-done">🟢 완료 ({{ day_info.done_count }}/{{ day_info.total_count }})</span>
                                    {% elif day_info.is_missed %}
                                        <span class="status-badge badge-missed">🔴 미완료 ({{ day_info.done_count }}/{{ day_info.total_count }})</span>
                                    {% elif day_info.done_count > 0 %}
                                        <span class="status-badge badge-ongoing">🟡 진행 ({{ day_info.done_count }}/{{ day_info.total_count }})</span>
                                    {% endif %}
                                {% endif %}
                            </td>
                        {% endif %}
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <p style="font-size: 0.9em; color: #64748b; margin-top: 20px; text-align: center; font-weight: 500;">💡 날짜 칸을 누르면 해당 날짜의 체크리스트로 이동합니다.</p>

        ''' + SECRET_FOOTER_HTML + '''
    </div>
</body>
</html>
'''

SECRET_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오빠 전용 로그인</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #1e293b; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 35px; border-radius: 16px; width: 340px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; }
        h2 { color: #1e293b; margin-bottom: 8px; font-size: 1.4em; font-weight: 800; }
        p { color: #64748b; font-size: 0.9em; margin-bottom: 24px; }
        input[type="password"] { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 1em; margin-bottom: 15px; text-align: center; }
        button { width: 100%; background: #3b82f6; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 1em; cursor: pointer; transition: 0.2s; }
        button:hover { background: #2563eb; }
        .error { color: #ef4444; font-size: 0.85em; margin-bottom: 12px; font-weight: 500; }
        .back-link { display: block; margin-top: 20px; color: #94a3b8; text-decoration: none; font-size: 0.85em; font-weight: 500; }
        .back-link:hover { color: #64748b; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔒 오빠 전용 모니터링</h2>
        <p>비밀번호를 입력하세요</p>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post">
            <input type="password" name="password" placeholder="비밀번호 입력" required autofocus>
            <button type="submit">접속하기</button>
        </form>
        <a href="/" class="back-link">← 홈으로 돌아가기</a>
    </div>
</body>
</html>
'''

ADMIN_PANEL_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오빠 전용 비밀 패널</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background-color: #f0f4f8; margin: 0; padding: 15px; color: #333; }
        .container { max-width: 550px; margin: auto; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 12px; margin-bottom: 18px; }
        h1 { font-size: 1.35em; color: #1e293b; margin: 0; font-weight: 800; }
        .logout-btn { background: #ef4444; color: white; padding: 6px 12px; border-radius: 8px; text-decoration: none; font-size: 0.85em; font-weight: bold; }
        .logout-btn:hover { background: #dc2626; }
        
        .summary-card { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 14px; margin-bottom: 18px; text-align: center; font-weight: bold; color: #1e40af; font-size: 0.95em; }
        
        .pw-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
        .pw-box h3 { font-size: 0.95em; margin: 0 0 12px 0; color: #1e293b; font-weight: 700; }
        .pw-input { width: 100%; padding: 9px 12px; margin-bottom: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.9em; }
        .pw-btn { background: #1e293b; color: white; border: none; padding: 10px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 0.9em; transition: 0.2s; }
        .pw-btn:hover { background: #334155; }
        
        .alert-success { background: #ecfdf5; color: #065f46; padding: 9px; border-radius: 6px; font-size: 0.85em; margin-bottom: 12px; text-align: center; font-weight: 500; border: 1px solid #a7f3d0; }
        .alert-error { background: #fef2f2; color: #991b1b; padding: 9px; border-radius: 6px; font-size: 0.85em; margin-bottom: 12px; text-align: center; font-weight: 500; border: 1px solid #fecaca; }

        .log-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-weight: bold; font-size: 0.95em; }
        
        .task-row { font-size: 0.88em; padding: 6px 0; color: #475569; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #f1f5f9; }
        .task-row:last-child { border-bottom: none; }
        
        .admin-toggle-btn { background: #3b82f6; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-size: 0.75em; font-weight: bold; cursor: pointer; }
        .admin-toggle-btn:hover { background: #2563eb; }
        .admin-toggle-btn.cancel { background: #64748b; }
        .admin-toggle-btn.cancel:hover { background: #475569; }

        .badge-ok { background: #ecfdf5; color: #059669; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 700; }
        .badge-no { background: #fef2f2; color: #dc2626; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 700; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕵️‍♂️ 오빠 전용 감시 패널</h1>
            <a href="/admin-logout" class="logout-btn">로그아웃</a>
        </div>

        <div class="summary-card">
            📊 최근 14일 중 총 <span style="color: #059669; font-size: 1.1em;">{{ total_completed_days }}일</span> 완벽 수행 완료!
        </div>

        <div class="pw-box">
            <h3>🔑 비밀번호 변경하기</h3>
            {% if success_msg %}
                <div class="alert-success">{{ success_msg }}</div>
            {% endif %}
            {% if error_msg %}
                <div class="alert-error">{{ error_msg }}</div>
            {% endif %}
            <form method="post">
                <input type="password" name="current_pw" class="pw-input" placeholder="현재 비밀번호" required>
                <input type="password" name="new_pw" class="pw-input" placeholder="새 비밀번호" required>
                <input type="password" name="confirm_pw" class="pw-input" placeholder="새 비밀번호 확인" required>
                <button type="submit" class="pw-btn">비밀번호 변경하기</button>
            </form>
        </div>

        <div>
            <h3 style="font-size: 1em; color: #1e293b; margin-bottom: 12px;">📅 날짜별 상세 기록 및 수정</h3>
            {% for log in history_logs %}
            <div class="log-card">
                <div class="log-header">
                    <span style="color: #1e293b;">{{ log.display }}</span>
                    {% if log.is_completed %}
                        <span class="badge-ok">🟢 완료 ({{ log.done_count }}/{{ log.total_count }})</span>
                    {% else %}
                        <span class="badge-no">🔴 미완료 ({{ log.done_count }}/{{ log.total_count }})</span>
                    {% endif %}
                </div>
                <div>
                    {% for t in log.task_details %}
                    <div class="task-row">
                        <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; padding-right: 8px;">
                            <span>{% if t.done %}✅{% else %}⬜{% endif %}</span>
                            <span style="{% if t.done %}text-decoration: line-through; color: #94a3b8;{% else %}color: #334155;{% endif %}">{{ t.task }}</span>
                        </div>
                        <form action="/toggle_task/{{ t.id }}" method="post" style="margin: 0;">
                            <input type="hidden" name="date" value="{{ log.date }}">
                            <input type="hidden" name="from_admin" value="true">
                            {% if t.done %}
                                <button type="submit" class="admin-toggle-btn cancel">취소</button>
                            {% else %}
                                <button type="submit" class="admin-toggle-btn">완료로 변경</button>
                            {% endif %}
                        </form>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
