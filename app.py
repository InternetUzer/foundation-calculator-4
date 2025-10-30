import streamlit as st
import math
import pandas as pd
from db_utils import (save_design, get_all_designs, get_design_by_id, 
                      delete_design, get_regional_pricing, get_pricing_by_region)
from pdf_generator import generate_pdf_report
from diagram_generator import create_foundation_diagram
import os

def calc_slab_fundament(A, B, H, rebar_diameter, grid_x, grid_y,
                        concrete_price, steel_price, formwork_price, waste_factor):
    volume_bet = A * B * H * (1 + waste_factor)

    area_bottom = A * B
    area_sides = 2 * (A + B) * H
    area_formwork = area_bottom + area_sides

    d_m = rebar_diameter / 1000.0
    n_x = math.ceil(B / grid_x) + 1
    n_y = math.ceil(A / grid_y) + 1
    length_x = n_x * A
    length_y = n_y * B
    length_rebar = length_x + length_y

    cross_section_area = math.pi * (d_m ** 2) / 4
    density_steel = 7850
    mass_rebar = length_rebar * cross_section_area * density_steel

    cost_concrete = volume_bet * concrete_price
    cost_steel = mass_rebar * steel_price
    cost_formwork = area_formwork * formwork_price
    cost_total = cost_concrete + cost_steel + cost_formwork

    return {
        'volume_bet': volume_bet,
        'area_formwork': area_formwork,
        'length_rebar': length_rebar,
        'mass_rebar': mass_rebar,
        'cost_concrete': cost_concrete,
        'cost_steel': cost_steel,
        'cost_formwork': cost_formwork,
        'cost_total': cost_total
    }

st.set_page_config(page_title="Калькулятор фундамента", page_icon="🏗️", layout="wide")

st.title("🏗️ Калькулятор плитного фундамента")

tab1, tab2, tab3 = st.tabs(["📊 Калькулятор", "💾 Сохраненные проекты", "📈 История расчетов"])

with tab1:
    st.markdown("---")
    
    col_settings1, col_settings2 = st.columns([1, 1])
    
    with col_settings1:
        use_regional = st.checkbox("🌍 Использовать региональные цены")
        
        if use_regional:
            try:
                regional_prices = get_regional_pricing()
                region_names = [r['region_name'] for r in regional_prices]
                selected_region = st.selectbox("Выберите регион", region_names)
                
                if selected_region:
                    pricing = get_pricing_by_region(selected_region)
                    st.info(f"Загружены цены для региона: {selected_region}")
            except Exception as e:
                st.error(f"❌ Ошибка загрузки региональных цен: {str(e)}")
                use_regional = False
        
        load_design = st.checkbox("📂 Загрузить сохраненный проект")
        
        if load_design:
            try:
                designs = get_all_designs()
                if designs:
                    design_options = {f"{d['name']} (ID: {d['id']})": d['id'] for d in designs}
                    selected_design_name = st.selectbox("Выберите проект", list(design_options.keys()))
                    
                    if st.button("Загрузить проект"):
                        design_id = design_options[selected_design_name]
                        loaded_design = get_design_by_id(design_id)
                        
                        if loaded_design:
                            st.session_state['loaded_design'] = loaded_design
                            st.success(f"✅ Проект '{loaded_design['name']}' загружен!")
                            st.rerun()
                else:
                    st.warning("Нет сохраненных проектов")
            except Exception as e:
                st.error(f"❌ Ошибка загрузки проектов: {str(e)}")
    
    if 'loaded_design' in st.session_state:
        ld = st.session_state['loaded_design']
        default_A = float(ld['length_a'])
        default_B = float(ld['width_b'])
        default_H = float(ld['thickness_h'])
        default_rebar = float(ld['rebar_diameter'])
        default_grid_x = float(ld['grid_x'])
        default_grid_y = float(ld['grid_y'])
        default_concrete_price = float(ld['concrete_price'])
        default_steel_price = float(ld['steel_price'])
        default_formwork_price = float(ld['formwork_price'])
        default_waste = float(ld['waste_factor']) * 100
    elif use_regional and selected_region:
        default_A = 10.0
        default_B = 8.0
        default_H = 0.3
        default_rebar = 12.0
        default_grid_x = 0.2
        default_grid_y = 0.2
        default_concrete_price = float(pricing['concrete_price'])
        default_steel_price = float(pricing['steel_price'])
        default_formwork_price = float(pricing['formwork_price'])
        default_waste = 5.0
    else:
        default_A = 10.0
        default_B = 8.0
        default_H = 0.3
        default_rebar = 12.0
        default_grid_x = 0.2
        default_grid_y = 0.2
        default_concrete_price = 4500.0
        default_steel_price = 50.0
        default_formwork_price = 350.0
        default_waste = 5.0
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📏 Размеры плиты")
        A = st.number_input("Длина плиты (м)", min_value=0.1, value=default_A, step=0.1, format="%.2f")
        B = st.number_input("Ширина плиты (м)", min_value=0.1, value=default_B, step=0.1, format="%.2f")
        H = st.number_input("Толщина плиты (м)", min_value=0.01, value=default_H, step=0.01, format="%.2f")
        
        st.subheader("🔩 Параметры арматуры")
        rebar_diameter = st.number_input("Диаметр арматуры (мм)", min_value=1.0, value=default_rebar, step=1.0, format="%.1f")
        grid_x = st.number_input("Шаг сетки по X (м)", min_value=0.1, value=default_grid_x, step=0.05, format="%.2f")
        grid_y = st.number_input("Шаг сетки по Y (м)", min_value=0.1, value=default_grid_y, step=0.05, format="%.2f")

    with col2:
        st.subheader("💰 Цены материалов")
        concrete_price = st.number_input("Цена бетона за м³ (руб)", min_value=0.0, value=default_concrete_price, step=100.0, format="%.2f")
        steel_price = st.number_input("Цена арматуры за кг (руб)", min_value=0.0, value=default_steel_price, step=1.0, format="%.2f")
        formwork_price = st.number_input("Цена опалубки за м² (руб)", min_value=0.0, value=default_formwork_price, step=10.0, format="%.2f")
        
        st.subheader("📊 Запас материалов")
        waste_factor_percent = st.number_input("Процент запаса материалов (%)", min_value=0.0, value=default_waste, step=1.0, format="%.1f")
        waste_factor = waste_factor_percent / 100.0

    st.markdown("---")

    if st.button("🧮 Рассчитать", type="primary", use_container_width=True):
        results = calc_slab_fundament(A, B, H, rebar_diameter, grid_x, grid_y,
                                      concrete_price, steel_price, formwork_price, waste_factor)
        
        st.session_state['current_results'] = results
        st.session_state['current_params'] = {
            'A': A, 'B': B, 'H': H, 'rebar_diameter': rebar_diameter,
            'grid_x': grid_x, 'grid_y': grid_y, 'concrete_price': concrete_price,
            'steel_price': steel_price, 'formwork_price': formwork_price,
            'waste_factor': waste_factor
        }
        
        st.success("✅ Расчет выполнен успешно!")

    if 'current_results' in st.session_state:
        results = st.session_state['current_results']
        params = st.session_state['current_params']
        
        st.markdown("---")
        st.header("📋 Результаты расчета")
        
        st.subheader("🏗️ Материалы")
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            st.metric("Объём бетона", f"{results['volume_bet']:.2f} м³")
        
        with col_m2:
            st.metric("Площадь опалубки", f"{results['area_formwork']:.2f} м²")
        
        with col_m3:
            st.metric("Длина арматуры", f"{results['length_rebar']:.2f} м")
        
        st.metric("Масса арматуры", f"{results['mass_rebar']:.2f} кг")
        
        st.markdown("---")
        
        st.subheader("💵 Стоимость")
        col_c1, col_c2, col_c3 = st.columns(3)
        
        with col_c1:
            st.metric("Стоимость бетона", f"{results['cost_concrete']:,.2f} руб")
        
        with col_c2:
            st.metric("Стоимость арматуры", f"{results['cost_steel']:,.2f} руб")
        
        with col_c3:
            st.metric("Стоимость опалубки", f"{results['cost_formwork']:,.2f} руб")
        
        st.markdown("---")
        
        st.subheader("💰 Итого")
        st.markdown(f"### **{results['cost_total']:,.2f} руб**")
        
        st.markdown("---")
        
        st.subheader("🎨 Визуализация фундамента")
        diagram_file = create_foundation_diagram(params['A'], params['B'], params['H'], 
                                                  params['rebar_diameter'], params['grid_x'], params['grid_y'])
        st.image(diagram_file, use_container_width=True)
        
        st.markdown("---")
        
        col_action1, col_action2, col_action3 = st.columns(3)
        
        with col_action1:
            design_name = st.text_input("Название проекта", value="Мой фундамент")
            if st.button("💾 Сохранить проект", use_container_width=True):
                try:
                    design_id = save_design(design_name, params, results)
                    st.success(f"✅ Проект сохранен! ID: {design_id}")
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")
        
        with col_action2:
            if st.button("📄 Сгенерировать PDF", use_container_width=True):
                try:
                    pdf_file = generate_pdf_report(params, results)
                    with open(pdf_file, "rb") as f:
                        st.session_state['pdf_data'] = f.read()
                    st.success("✅ PDF отчет готов!")
                except Exception as e:
                    st.error(f"Ошибка генерации PDF: {e}")
            
            if 'pdf_data' in st.session_state:
                st.download_button(
                    label="⬇️ Скачать PDF отчет",
                    data=st.session_state['pdf_data'],
                    file_name="foundation_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="pdf_download"
                )
        
        with col_action3:
            if st.button("📊 Экспорт в CSV", use_container_width=True):
                try:
                    export_data = {
                        "Параметр": [
                            "Длина (м)", "Ширина (м)", "Толщина (м)",
                            "Диаметр арматуры (мм)", "Шаг X (м)", "Шаг Y (м)",
                            "Цена бетона (руб/м³)", "Цена арматуры (руб/кг)",
                            "Цена опалубки (руб/м²)", "Запас (%)",
                            "", "Объём бетона (м³)", "Площадь опалубки (м²)",
                            "Длина арматуры (м)", "Масса арматуры (кг)",
                            "Стоимость бетона (руб)", "Стоимость арматуры (руб)",
                            "Стоимость опалубки (руб)", "ИТОГО (руб)"
                        ],
                        "Значение": [
                            params['A'], params['B'], params['H'],
                            params['rebar_diameter'], params['grid_x'], params['grid_y'],
                            params['concrete_price'], params['steel_price'],
                            params['formwork_price'], params['waste_factor']*100,
                            "", results['volume_bet'], results['area_formwork'],
                            results['length_rebar'], results['mass_rebar'],
                            results['cost_concrete'], results['cost_steel'],
                            results['cost_formwork'], results['cost_total']
                        ]
                    }
                    df_export = pd.DataFrame(export_data)
                    st.session_state['csv_data'] = df_export.to_csv(index=False, encoding='utf-8-sig')
                    st.success("✅ CSV готов к скачиванию!")
                except Exception as e:
                    st.error(f"Ошибка экспорта: {e}")
            
            if 'csv_data' in st.session_state:
                st.download_button(
                    label="⬇️ Скачать CSV",
                    data=st.session_state['csv_data'],
                    file_name="foundation_calculation.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="csv_download"
                )
        
        st.markdown("---")
        st.subheader("📊 Детализация расчета")
        
        data = {
            "Параметр": [
                "Объём бетона", "Площадь опалубки", "Общая длина арматуры",
                "Масса арматуры", "Стоимость бетона", "Стоимость арматуры",
                "Стоимость опалубки", "Итоговая стоимость"
            ],
            "Значение": [
                f"{results['volume_bet']:.2f} м³",
                f"{results['area_formwork']:.2f} м²",
                f"{results['length_rebar']:.2f} м",
                f"{results['mass_rebar']:.2f} кг",
                f"{results['cost_concrete']:,.2f} руб",
                f"{results['cost_steel']:,.2f} руб",
                f"{results['cost_formwork']:,.2f} руб",
                f"{results['cost_total']:,.2f} руб"
            ]
        }
        
        df = pd.DataFrame(data)
        st.table(df)
    else:
        st.info("👆 Введите параметры и нажмите кнопку 'Рассчитать' для получения результатов")

with tab2:
    st.header("💾 Сохраненные проекты")
    
    try:
        designs = get_all_designs()
        
        if designs:
            st.write(f"Всего сохранено проектов: **{len(designs)}**")
            st.markdown("---")
            
            for design in designs:
                with st.expander(f"📁 {design['name']} (ID: {design['id']}) - {design['created_at'].strftime('%d.%m.%Y %H:%M')}"):
                    col_d1, col_d2 = st.columns(2)
                    
                    with col_d1:
                        st.write("**Размеры:**")
                        st.write(f"- Длина: {design['length_a']} м")
                        st.write(f"- Ширина: {design['width_b']} м")
                        st.write(f"- Толщина: {design['thickness_h']} м")
                        
                        st.write("**Арматура:**")
                        st.write(f"- Диаметр: {design['rebar_diameter']} мм")
                        st.write(f"- Шаг X: {design['grid_x']} м")
                        st.write(f"- Шаг Y: {design['grid_y']} м")
                    
                    with col_d2:
                        st.write("**Стоимость:**")
                        st.write(f"- Бетон: {design['cost_concrete']:,.2f} руб")
                        st.write(f"- Арматура: {design['cost_steel']:,.2f} руб")
                        st.write(f"- Опалубка: {design['cost_formwork']:,.2f} руб")
                        st.write(f"**ИТОГО: {design['cost_total']:,.2f} руб**")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button(f"🗑️ Удалить", key=f"del_{design['id']}"):
                            try:
                                delete_design(design['id'])
                                st.success("Проект удален!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Ошибка удаления: {str(e)}")
                    
                    with col_btn2:
                        if st.button(f"📊 Загрузить в калькулятор", key=f"load_{design['id']}"):
                            st.session_state['loaded_design'] = design
                            st.success(f"Проект загружен! Перейдите на вкладку 'Калькулятор'")
        else:
            st.info("У вас пока нет сохраненных проектов")
    except Exception as e:
        st.error(f"❌ Ошибка загрузки проектов: {str(e)}")

with tab3:
    st.header("📈 История расчетов")
    
    try:
        designs = get_all_designs()
        
        if designs:
            history_data = {
            "ID": [d['id'] for d in designs],
            "Название": [d['name'] for d in designs],
            "Дата": [d['created_at'].strftime('%d.%m.%Y %H:%M') for d in designs],
            "Размер (ДxШxВ)": [f"{d['length_a']}x{d['width_b']}x{d['thickness_h']}" for d in designs],
            "Объём бетона (м³)": [f"{float(d['volume_bet']):.2f}" for d in designs],
            "Масса арматуры (кг)": [f"{float(d['mass_rebar']):.2f}" for d in designs],
            "Стоимость (руб)": [f"{float(d['cost_total']):,.2f}" for d in designs]
        }
        
            df_history = pd.DataFrame(history_data)
            st.dataframe(df_history, use_container_width=True)
            
            st.markdown("---")
            
            if st.button("📥 Подготовить экспорт истории в CSV"):
                st.session_state['history_csv'] = df_history.to_csv(index=False, encoding='utf-8-sig')
                st.success("✅ CSV готов к скачиванию!")
            
            if 'history_csv' in st.session_state:
                st.download_button(
                    label="⬇️ Скачать CSV истории",
                    data=st.session_state['history_csv'],
                    file_name="foundation_history.csv",
                    mime="text/csv",
                    key="history_csv_download"
                )
            
            st.markdown("---")
            st.subheader("📊 Сравнение проектов")
            
            if len(designs) >= 2:
                design_names = [f"{d['name']} (ID: {d['id']})" for d in designs]
                compare_designs = st.multiselect("Выберите проекты для сравнения (до 5)", design_names, max_selections=5)
                
                if len(compare_designs) >= 2:
                    selected_ids = [int(name.split("ID: ")[1].rstrip(")")) for name in compare_designs]
                    selected_designs = [d for d in designs if d['id'] in selected_ids]
                    
                    comparison_data = {
                        "Параметр": [
                            "Длина (м)", "Ширина (м)", "Толщина (м)",
                            "Объём бетона (м³)", "Масса арматуры (кг)",
                            "Стоимость бетона (руб)", "Стоимость арматуры (руб)",
                            "Стоимость опалубки (руб)", "ИТОГО (руб)"
                        ]
                    }
                    
                    for design in selected_designs:
                        comparison_data[design['name']] = [
                            float(design['length_a']),
                            float(design['width_b']),
                            float(design['thickness_h']),
                            float(design['volume_bet']),
                            float(design['mass_rebar']),
                            float(design['cost_concrete']),
                            float(design['cost_steel']),
                            float(design['cost_formwork']),
                            float(design['cost_total'])
                        ]
                    
                    df_comparison = pd.DataFrame(comparison_data)
                    st.table(df_comparison)
            else:
                st.info("Сохраните минимум 2 проекта для сравнения")
        else:
            st.info("История расчетов пуста")
    except Exception as e:
        st.error(f"❌ Ошибка загрузки истории: {str(e)}")
