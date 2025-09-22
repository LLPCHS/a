import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    visible: true
    width: 600
    height: 800
    title: "تنظیم تاریخ و ساعت"
    flags: Qt.FramelessWindowHint  // حذف نوار عنوان

    Component.onCompleted: {
        dateTimePopup.open()  // باز کردن خودکار پنجره تنظیم تاریخ و ساعت
    }

    // پنجره تنظیم تاریخ و ساعت
    Popup {
        id: dateTimePopup
        anchors.centerIn: parent
        width: 500
        height: 600
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose  // غیرفعال کردن بستن خودکار

        background: Rectangle {
            color: "#ffffff"
            radius: 10
            border.color: "#ccc"
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20

            Label {
                text: "تنظیم تاریخ و ساعت شمسی"
                font.pixelSize: 24
                Layout.alignment: Qt.AlignHCenter
                color: "#333"
            }

            // تاریخ شمسی
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10

                // سال
                ColumnLayout {
                    Label {
                        text: "سال"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Tumbler {
                        id: yearTumbler
                        model: 200 // از 1300 تا 1499
                        currentIndex: 104 // برای سال 1404
                        Layout.preferredWidth: 100
                        Layout.preferredHeight: 200
                        delegate: Text {
                            text: 1300 + index
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            color: yearTumbler.currentIndex === index ? "#4CAF50" : "#333"
                        }
                        onCurrentIndexChanged: {
                            controller.update_day_max(1300 + currentIndex, monthTumbler.currentIndex + 1)
                        }
                    }
                }

                // ماه
                ColumnLayout {
                    Label {
                        text: "ماه"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Tumbler {
                        id: monthTumbler
                        model: 12 // از 1 تا 12
                        currentIndex: 5 // برای ماه 6
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 200
                        delegate: Text {
                            text: index + 1
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            color: monthTumbler.currentIndex === index ? "#4CAF50" : "#333"
                        }
                        onCurrentIndexChanged: {
                            controller.update_day_max(1300 + yearTumbler.currentIndex, currentIndex + 1)
                        }
                    }
                }

                // روز
                ColumnLayout {
                    Label {
                        text: "روز"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Tumbler {
                        id: dayTumbler
                        model: 31 // به‌صورت پویا به‌روزرسانی می‌شود
                        currentIndex: 0 // برای روز 1
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 200
                        delegate: Text {
                            text: index + 1
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            color: dayTumbler.currentIndex === index ? "#4CAF50" : "#333"
                        }
                    }
                }
            }

            // ساعت
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10

                // ساعت
                ColumnLayout {
                    Label {
                        text: "ساعت"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Tumbler {
                        id: hourTumbler
                        model: 24 // از 0 تا 23
                        currentIndex: 0
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 200
                        delegate: Text {
                            text: index
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            color: hourTumbler.currentIndex === index ? "#4CAF50" : "#333"
                        }
                    }
                }

                // دقیقه
                ColumnLayout {
                    Label {
                        text: "دقیقه"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Tumbler {
                        id: minuteTumbler
                        model: 60 // از 0 تا 59
                        currentIndex: 0
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 200
                        delegate: Text {
                            text: index
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            color: minuteTumbler.currentIndex === index ? "#4CAF50" : "#333"
                        }
                    }
                }
            }

            // دکمه تنظیم
            Button {
                text: "تنظیم تاریخ و ساعت"
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 250
                Layout.preferredHeight: 60
                background: Rectangle {
                    color: "#4CAF50"
                    radius: 10
                }
                onClicked: {
                    controller.set_system_datetime(
                        1300 + yearTumbler.currentIndex,
                        monthTumbler.currentIndex + 1,
                        dayTumbler.currentIndex + 1,
                        hourTumbler.currentIndex,
                        minuteTumbler.currentIndex
                    )
                }
            }

            // پیام وضعیت
            Label {
                id: resultLabel
                text: ""
                font.pixelSize: 16
                Layout.alignment: Qt.AlignHCenter
                wrapMode: Text.Wrap
            }
        }
    }

    Connections {
        target: controller
        function onShowWarning() {
            dateTimePopup.open()  // باز کردن پنجره تنظیم تاریخ
        }
        function onUpdateDayMax(maxDay) {
            dayTumbler.model = maxDay
            if (dayTumbler.currentIndex >= maxDay) {
                dayTumbler.currentIndex = maxDay - 1
            }
        }
        function onUpdateDateTime(message, status) {
            resultLabel.text = message
            resultLabel.color = status === "success" ? "#4CAF50" : "#d32f2f"
        }
        function onCloseApplication() {
            console.log("Received closeApplication signal")  // برای دیباگ
            root.close()  // بستن پنجره اصلی
        }
    }
}