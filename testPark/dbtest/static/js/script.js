// static/js/script.js

let clothingRecommendation = "";
let lastAnswer = "";

function updateGu() {
    const city = document.getElementById("city").value;
    const guSelect = document.getElementById("gu");
    guSelect.innerHTML = "<option value=''>구/군 선택</option>";

    if (addressData[city]) {
        Object.keys(addressData[city]).forEach(gu => {
            const option = document.createElement("option");
            option.value = gu;
            option.textContent = gu;
            guSelect.appendChild(option);
        });
    }
    document.getElementById("dong").innerHTML = "<option value=''>읍/면/동 선택</option>";
}

function updateDong() {
    const city = document.getElementById("city").value;
    const gu = document.getElementById("gu").value;
    const dongSelect = document.getElementById("dong");
    dongSelect.innerHTML = "<option value=''>읍/면/동 선택</option>";

    if (addressData[city] && addressData[city][gu]) {
        addressData[city][gu].forEach(dong => {
            const option = document.createElement("option");
            option.value = dong;
            option.textContent = dong;
            dongSelect.appendChild(option);
        });
    }
}

function handleLoading(event) {
    event.preventDefault(); // 폼 제출 기본 동작 방지
    const button = document.getElementById('searchButton');

    // 버튼 비활성화 및 텍스트 변경
    button.disabled = true;
    button.textContent = '조회 중...';

    // 로딩 스피너 추가
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    button.appendChild(spinner);

    // 서버 요청 로직 추가 (예시: 폼 제출 시 실제 작업 처리)
    setTimeout(() => {
        document.querySelector('form').submit(); // 폼 제출
    }, 1000); // 요청 지연 시뮬레이션
}

async function getWeather() {
    const city = document.getElementById("city").value;
    const gu = document.getElementById("gu").value;
    const dong = document.getElementById("dong").value;

    if (!city || !gu || !dong) {
        alert("모든 항목을 선택해 주세요.");
        return;
    }

    const button = document.querySelector("button");
    button.disabled = true;
    button.textContent = "조회 중...";

    try {
        const coordsResponse = await fetch('/get_coords', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({city, gu, dong})
        });

        const coordsData = await coordsResponse.json();
        if (coordsResponse.ok) {
            const {lat, lon} = coordsData;
            const weatherResponse = await fetch('/get_weather', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lat, lon})
            });

            const weatherData = await weatherResponse.json();
            if (weatherResponse.ok) {
                hideSelectionUI();
                clothingRecommendation = weatherData.clothing_recommendation;
                displayResult(city, gu, dong, lat, lon, weatherData);

                const chatButton = document.querySelector(".open-chat-btn");
                const chatSidebar = document.getElementById("chatSidebar");
                chatButton.style.display = "block";
                chatSidebar.style.display = "block";

            } else {
                alert(weatherData.error);
            }
        } else {
            alert(coordsData.error);
        }
    } catch (error) {
        console.error("오류 발생:", error);
        alert("서버와의 통신 중 오류가 발생했습니다.");
    } finally {
        button.disabled = false;
        button.textContent = "조회";
    }
}

function setupHourlyWeatherListener(hourlyData) {
    const weatherBox = document.querySelector('.result .box:nth-child(2)'); // 날씨 정보 박스
    weatherBox.style.cursor = "pointer";
    weatherBox.title = "시간별 날씨 보기";
    weatherBox.onclick = () => displayHourlyWeather(hourlyData);
}

function displayHourlyWeather(hourlyData) {
    console.log("원본 시간별 데이터:", hourlyData);

    const futureData = filterFutureWeather(hourlyData);
    console.log("필터링된 시간별 데이터:", futureData);

    const modal = document.getElementById("hourlyWeatherModal");
    const modalContent = document.getElementById("hourlyWeatherContent");

    if (!futureData || futureData.length === 0) {
        modalContent.innerHTML = "<p>시간별 데이터가 없습니다.</p>";
    } else {
        modalContent.innerHTML = `
            <div class="hourly-weather-row">
              ${futureData.map(hour => `
                <div class="hourly-weather-card">
                   <p><strong>${formatTime(hour.time)}</strong></p>
                   <p>${hour.temperature}°C</p>
                </div>
              `).join('')}
            </div>
          `;
    }

    modal.style.display = "flex";
}

function filterFutureWeather(hourlyData) {
    const now = new Date(); // 현재 시각
    const currentHour = now.getHours(); // 현재 시간 (24시간 형식)
    const currentMinute = now.getMinutes(); // 현재 분

    // 현재 시각을 HHMM 형식으로 변환
    const currentTime = `${currentHour.toString().padStart(2, '0')}${currentMinute >= 30 ? '30' : '00'}`;

    // 현재 시각 이후의 데이터만 필터링
    return hourlyData.filter(hour => parseInt(hour.time, 10) >= parseInt(currentTime, 10));
}

function closeModal() {
    const modal = document.getElementById("hourlyWeatherModal");
    modal.style.display = "none";
}

function hideSelectionUI() {
    document.getElementById("city").style.display = "none";
    document.getElementById("gu").style.display = "none";
    document.getElementById("dong").style.display = "none";
    document.querySelector("button").style.display = "none";
}

function formatTime(time) {
    // 시간 값이 문자열로 들어올 경우 숫자로 변환
    time = time.toString();

    // 앞 두 자리(시)와 뒤 두 자리(분)로 분리
    const hours = time.slice(0, 2);
    const minutes = time.slice(2, 4);


    return `${hours}:${minutes}`;
}

function displayResult(city, gu, dong, lat, lon, weatherData) {
    const resultDiv = document.querySelector(".result");
    resultDiv.style.display = "block";
    resultDiv.style.opacity = "1";

    const formattedClothingRecommendation = weatherData.clothing_recommendation
        .split('\n')
        .map(line =>
            line.replace(/:/g, ':<br>')
                .replace(/,/g, ',<br>')
                .replace(/- /g, '<br>- ')
        )
        .join('<br>');

    resultDiv.innerHTML = `
    <div class="box">
      <h2>선택된 위치</h2>
      <p>${city} > ${gu} > ${dong}</p>
      <p>위도: ${lat}<br> 경도: ${lon}</p>
    </div>
    <div class="box">
      <h2>날씨 정보</h2>
      <p>온도: ${weatherData.temperature}°C</p>
      <p>날씨 상태: ${weatherData.sky_status}</p>
      <p>풍속: ${weatherData.wind_speed} m/s</p>
      <p>강수 형태: ${weatherData.precipitation_type}</p>
      <p>강수 확률: ${weatherData.precipitation_probability}%</p>
      <p>습도: ${weatherData.humidity}%</p>
    </div>
    <div class="box">
      <h2>추천 의류</h2>
      <p>${formattedClothingRecommendation}</p>
    </div>
  `;

    console.log("시간별 데이터 확인:", weatherData.hourly);
    setupHourlyWeatherListener(weatherData.hourly); // 추가

}

function toggleChat() {
    const chatSidebar = document.getElementById("chatSidebar");
    const chatButton = document.querySelector(".open-chat-btn");
    const overlay = document.getElementById("overlay");
    const body = document.body;

    if (chatSidebar.style.right === "0px") {
        chatSidebar.style.right = "-100%";
        chatButton.innerHTML = '<i class="fa fa-comments"></i>';
        overlay.style.display = "none";
        body.classList.remove("blurred");
    } else {
        chatSidebar.style.right = "0px";
        chatButton.innerHTML = '<i class="fa fa-home"></i>';
        overlay.style.display = "block";
        body.classList.add("blurred");
    }
}
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// 2024-11-28 추가 수정 !!!!!!!!!!!
async function askQuestion() {
    const userQuestion = document.getElementById("userQuestion").value;
    const chatResponse = document.getElementById("chatResponse");

    if (!userQuestion) {
        alert("질문을 입력해 주세요.");
        return;
    }

    const userBubble = document.createElement("p");
    userBubble.className = "user";
    userBubble.innerHTML = `<span>${userQuestion}</span>`;
    chatResponse.appendChild(userBubble);

    document.getElementById("userQuestion").value = "";

    try {
        const response = await fetch('/ask_question', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: userQuestion})
        });

        const data = await response.json();
        lastAnswer = data.answer;

        const botBubble = document.createElement("p");
        botBubble.className = "bot";
        botBubble.innerHTML = `<span style="white-space: pre-line;">${data.answer}</span>`;
        chatResponse.appendChild(botBubble);

    } catch (error) {
        console.error("오류 발생:", error);
        const errorBubble = document.createElement("p");
        errorBubble.className = "bot";
        errorBubble.innerHTML = `<span style="white-space: pre-line;">오류가 발생했습니다. 다시 시도해 주세요.</span>`;
        chatResponse.appendChild(errorBubble);
    }
    chatResponse.scrollTop = chatResponse.scrollHeight;
}
/////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////
// 2024-11-28 추가 수정

function createRecommendationButtons() {
    const chatResponse = document.getElementById("chatResponse");

    // 버튼 컨테이너 생성
    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = "flex";
    buttonContainer.style.justifyContent = "center";
    buttonContainer.style.gap = "10px";
    buttonContainer.style.marginTop = "10px";

    // 시간별 추천 보기 버튼
    const hourlyButton = document.createElement("button");
    hourlyButton.textContent = "시간별 추천 보기";
    hourlyButton.onclick = requestHourlyRecommendation;
    hourlyButton.style.padding = "10px 15px";
    hourlyButton.style.fontSize = "14px";
    hourlyButton.style.borderRadius = "10px";
    hourlyButton.style.border = "none";
    hourlyButton.style.backgroundColor = "#787878";
    hourlyButton.style.color = "white";
    hourlyButton.style.cursor = "pointer";
    hourlyButton.onmouseover = () => (hourlyButton.style.backgroundColor = "#646464");
    hourlyButton.onmouseout = () => (hourlyButton.style.backgroundColor = "#787878");

    // 현재 날씨 추천 보기 버튼
    const currentButton = document.createElement("button");
    currentButton.textContent = "현재 날씨 추천 보기";
    currentButton.onclick = requestCurrentRecommendation;
    currentButton.style.padding = "10px 15px";
    currentButton.style.fontSize = "14px";
    currentButton.style.borderRadius = "10px";
    currentButton.style.border = "none";
    currentButton.style.backgroundColor = "#787878";
    currentButton.style.color = "white";
    currentButton.style.cursor = "pointer";
    currentButton.onmouseover = () => (currentButton.style.backgroundColor = "#646464");
    currentButton.onmouseout = () => (currentButton.style.backgroundColor = "#787878");

    // 버튼을 컨테이너에 추가
    buttonContainer.appendChild(hourlyButton);
    buttonContainer.appendChild(currentButton);

    // 버튼 컨테이너를 응답 영역에 추가
    chatResponse.appendChild(buttonContainer);
}

// 채팅 박스가 로드될 때 버튼 생성
window.onload = function () {
    createRecommendationButtons();
};

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function requestHourlyRecommendation() {
    const chatResponse = document.getElementById("chatResponse");
    const userBubble = document.createElement("p");
    userBubble.className = "user";
    userBubble.innerHTML = `<span>시간별 의류 추천을 보여줘.</span>`;
    chatResponse.appendChild(userBubble);

    fetch('/ask_question', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: "시간별 의류 추천을 보여줘."})
    })
        .then(response => response.json())
        .then(data => {
            const botBubble = document.createElement("p");
            botBubble.className = "bot";
            botBubble.innerHTML = `<span style="white-space: pre-line;">${data.answer}</span>`;
            chatResponse.appendChild(botBubble);
        })
        .catch(error => {
            console.error("오류 발생:", error);
            const errorBubble = document.createElement("p");
            errorBubble.className = "bot";
            errorBubble.innerHTML = `<span style="white-space: pre-line;">오류가 발생했습니다. 다시 시도해 주세요.</span>`;
            chatResponse.appendChild(errorBubble);
        });
}

function requestCurrentRecommendation() {
    const chatResponse = document.getElementById("chatResponse");
    const userBubble = document.createElement("p");
    userBubble.className = "user";
    userBubble.innerHTML = `<span>현재 날씨에 따른 의류 추천을 보여줘.</span>`;
    chatResponse.appendChild(userBubble);

    fetch('/ask_question', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: "현재 날씨에 따른 의류 추천을 보여줘."})
    })
        .then(response => response.json())
        .then(data => {
            const botBubble = document.createElement("p");
            botBubble.className = "bot";
            botBubble.innerHTML = `<span style="white-space: pre-line;">${data.answer}</span>`;
            chatResponse.appendChild(botBubble);
        })
        .catch(error => {
            console.error("오류 발생:", error);
            const errorBubble = document.createElement("p");
            errorBubble.className = "bot";
            errorBubble.innerHTML = `<span style="white-space: pre-line;">오류가 발생했습니다. 다시 시도해 주세요.</span>`;
            chatResponse.appendChild(errorBubble);
        });
}

// 여기까지 /////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
window.onload = function () {
    const citySelect = document.getElementById("city");
    Object.keys(addressData).forEach(city => {
        if (city !== "Column3") {
            const option = document.createElement("option");
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        }
    });

    citySelect.addEventListener("change", updateGu);
    document.getElementById("gu").addEventListener("change", updateDong);
};

// 의류 저장 함수
function saveClothing() {
    fetch('/save_clothing', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({clothing: lastAnswer})
    })
        .then(response => response.json())
        .then(data => alert(data.message))
        .catch(error => console.error('오류 발생:', error));
}

// 로그인 함수
async function getLogin() {
    const login_id = document.getElementById("login_id").value;
    const login_ps = document.getElementById("login_ps").value;

    const response = await fetch('/login', {
        method: 'POST',
        headers: {
            'Content-type': 'application/json'
        },
        body: JSON.stringify({login_id, login_ps})
    });
    const result = await response.json();
    document.getElementById("result").innerText = result.message;
}

// 시간별 날씨 스크롤 함수
function scrollHourly(direction) {
    const row = document.querySelector('.hourly-weather-row');
    const scrollAmount = 200; // 스크롤 이동 픽셀 수
    row.scrollBy({
        left: scrollAmount * direction,
        behavior: 'smooth',
    });
}

// 스냅샷 이미지 로드
document.addEventListener("DOMContentLoaded", () => {
    const snapshotImagesContainer = document.getElementById("snapshotImages");
    const jsonFilePath = "/static/images/image_urls.json"; // JSON 파일 경로

    // 배열 섞기 함수 (Fisher-Yates 알고리즘)
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    // 무한 스크롤 구현
    fetch(jsonFilePath)
        .then(response => response.json())
        .then(data => {
            let imageUrls = data.images;

            // 이미지 순서 섞기
            imageUrls = shuffleArray(imageUrls);

            // 원본 배열 앞뒤에 복제 이미지 추가
            const extendedImages = [...imageUrls.slice(-3), ...imageUrls, ...imageUrls.slice(0, 3)];

            // 이미지 요소 생성 및 추가
            extendedImages.forEach(url => {
                const imgElement = document.createElement("img");
                imgElement.src = url;
                imgElement.className = "snapshot-image";
                snapshotImagesContainer.appendChild(imgElement);
            });

            // 슬라이더 초기화
            initInfiniteScroll(imageUrls.length);
        })
        .catch(error => console.error("Error loading JSON:", error));
});

function initInfiniteScroll(originalLength) {
    const slider = document.getElementById("snapshotImages");
    const images = document.querySelectorAll(".snapshot-image");

    let currentIndex = 3; // 중간의 첫 번째 원본 이미지 인덱스
    const imageWidth = images[0].clientWidth + 20; // 이미지 너비 + 간격
    slider.style.transform = `translateX(-${currentIndex * imageWidth}px)`;

    // 슬라이더 이동 함수
    function scrollSnapshot(direction) {
        currentIndex += direction;

        // 슬라이더 이동
        slider.style.transition = "transform 0.3s ease-in-out";
        slider.style.transform = `translateX(-${currentIndex * imageWidth}px)`;
    }

    // `transitionend` 이벤트로 위치 조정
    slider.addEventListener("transitionend", () => {
        if (currentIndex < 2) {
            // 앞쪽으로 이동 시 복제된 끝으로 점프
            slider.style.transition = "none"; // 애니메이션 제거
            currentIndex += originalLength; // 뒤쪽으로 이동
            slider.style.transform = `translateX(-${currentIndex * imageWidth}px)`;
        } else if (currentIndex >= 2 + originalLength) {
            // 뒤쪽으로 이동 시 복제된 앞쪽으로 점프
            slider.style.transition = "none"; // 애니메이션 제거
            currentIndex -= originalLength; // 앞쪽으로 이동
            slider.style.transform = `translateX(-${currentIndex * imageWidth}px)`;
        }
    });

    // 버튼 클릭 이벤트 연결
    document.querySelector(".scroll-button.left").onclick = () => scrollSnapshot(-1);
    document.querySelector(".scroll-button.right").onclick = () => scrollSnapshot(1);
}


// 성별 카테고리 변경
function changeGenderCategory(gender) {
    const genderButtons = document.querySelectorAll('.gender-category .filter-button');

    // 성별 버튼 활성화
    genderButtons.forEach(btn => btn.classList.remove('active'));
    genderButtons.forEach(btn => {
        if (btn.textContent === gender) {
            btn.classList.add('active');
        }
    });

    console.log(`Gender category changed to: ${gender}`);
}

// 상위 카테고리 변경
function changeMainCategory(category) {
    const mainButtons = document.querySelectorAll('.main-category .filter-button');
    const subButtons = document.querySelectorAll('.sub-category .filter-button');

    // 상위 버튼 활성화
    mainButtons.forEach(btn => btn.classList.remove('active'));
    mainButtons.forEach(btn => {
        if (btn.textContent === category) {
            btn.classList.add('active');
        }
    });

    // 하위 버튼 초기화
    subButtons.forEach(btn => btn.classList.remove('active'));
    console.log(`Main category changed to: ${category}`);
}

// 하위 카테고리 선택
function selectSubCategory(subCategory) {
    const subButtons = document.querySelectorAll('.sub-category .filter-button');

    // 하위 버튼 활성화
    subButtons.forEach(btn => btn.classList.remove('active'));
    subButtons.forEach(btn => {
        if (btn.textContent === subCategory) {
            btn.classList.add('active');
        }
    });

    console.log(`Sub category selected: ${subCategory}`);
}


// // 스냅샷 스크롤 버튼 (추가적인 동작을 여기에 구현)
// function scrollSnapshot(direction) {
//     const slider = document.getElementById('snapshotImages');
//     const slideWidth = slider.firstElementChild?.offsetWidth || 300;
//
//     const currentTransform = getComputedStyle(slider).transform;
//     const matrix = new DOMMatrix(currentTransform);
//     const currentTranslateX = matrix.m41;
//
//     slider.style.transform = `translateX(${currentTranslateX + direction * slideWidth}px)`;
//     console.log(`Scrolled ${direction > 0 ? 'right' : 'left'}`);
// }
//
