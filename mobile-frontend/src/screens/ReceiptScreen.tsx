import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { User } from 'lucide-react-native';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Receipt'>;
  route: RouteProp<RootStackParamList, 'Receipt'>;
};

export default function ReceiptScreen({ navigation, route }: Props) {
  const insets = useSafeAreaInsets();
  const { receiptData, sessionData } = route.params;

  const handleDownloadPDF = async () => {
    try {
      const isAdditional = receiptData.payment_type === 'additional';
      const paymentLabel = isAdditional ? 'Additional Payment' : 'Original Payment';
      const accent = isAdditional ? '#dc3545' : '#007BFF';

      const html = `
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
              body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 30px; color: #1a1a1a; background: #fff; }
              .header { text-align: center; margin-bottom: 30px; }
              .header h1 { font-size: 22px; margin: 0 0 4px; }
              .header p { font-size: 13px; color: #666; margin: 0; }
              .accent-bar { height: 4px; background: ${accent}; border-radius: 4px; margin-bottom: 24px; }
              .badge { display: inline-block; padding: 4px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 20px; background: ${isAdditional ? '#FFF3CD' : '#E8F5E9'}; color: ${isAdditional ? '#856404' : '#2E7D32'}; }
              .card { border: 1px solid #e5e5e5; border-radius: 12px; overflow: hidden; margin-bottom: 20px; }
              .card-body { padding: 20px; }
              .row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed #e0e0e0; }
              .row:last-child { border-bottom: none; }
              .label { color: #888; font-size: 14px; }
              .value { font-weight: 700; font-size: 14px; text-align: right; }
              .total-row { display: flex; justify-content: space-between; align-items: center; padding: 16px 0 0; margin-top: 8px; border-top: 2px solid #e0e0e0; }
              .total-label { font-size: 16px; font-weight: 700; }
              .total-value { font-size: 24px; font-weight: 700; color: ${accent}; }
              .info-box { background: #EBF5FF; padding: 14px; border-radius: 8px; text-align: center; font-size: 12px; color: #0056b3; margin-bottom: 16px; }
              .footer { text-align: center; font-size: 11px; color: #aaa; margin-top: 30px; }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>SmartPark</h1>
              <p>Parking Receipt</p>
            </div>
            <div class="accent-bar"></div>
            <div style="text-align:center;"><span class="badge">${paymentLabel}</span></div>
            <div class="card">
              <div class="card-body">
                ${receiptData.receipt_number ? `<div class="row"><span class="label">Receipt No.</span><span class="value">${receiptData.receipt_number}</span></div>` : ''}
                <div class="row"><span class="label">License Plate</span><span class="value">${sessionData.license_plate}</span></div>
                <div class="row"><span class="label">Entry Time</span><span class="value">${formatDate(sessionData.entry_time)}</span></div>
                <div class="row"><span class="label">Payment Date</span><span class="value">${formatDate(receiptData.payment_date)}</span></div>
                <div class="row"><span class="label">Payment Method</span><span class="value">${receiptData.payment_method}</span></div>
                <div class="total-row">
                  <span class="total-label">TOTAL PAID</span>
                  <span class="total-value">RM ${Number(receiptData.total_amount).toFixed(2)}</span>
                </div>
              </div>
            </div>
            ${sessionData.grace_end_time ? `<div class="info-box"><strong>Grace Period Deadline</strong><br/>Please exit before ${formatDate(sessionData.grace_end_time)}</div>` : ''}
            <div class="info-box">Please exit the parking area within 15 minutes of payment.</div>
            <div class="footer">Thank you for using SmartPark</div>
          </body>
        </html>
      `;

      const { uri } = await Print.printToFileAsync({ html });

      // Move the PDF to a shareable location (fixes Android permission error)
      const pdfName = `SmartPark_Receipt_${receiptData.receipt_number || Date.now()}.pdf`;
      const shareableUri = `${FileSystem.documentDirectory}${pdfName}`;
      await FileSystem.moveAsync({ from: uri, to: shareableUri });

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(shareableUri, {
          mimeType: 'application/pdf',
          dialogTitle: 'Save or Share Receipt PDF',
          UTI: 'com.adobe.pdf',
        });
      } else {
        Alert.alert('Success', `PDF saved to: ${shareableUri}`);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to generate PDF. Please try again.');
      console.error('PDF generation error:', error);
    }
  };

  const handleReturnHome = () => {
    navigation.reset({
      index: 0,
      routes: [{ name: 'DriverLogin' }],
    });
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    let normalized = dateString;
    if (!normalized.includes('T')) normalized = normalized.replace(' ', 'T');
    if (!normalized.endsWith('Z') && !normalized.includes('+')) normalized += 'Z';

    const date = new Date(normalized);
    // Add 8 hours for Malaysia Time
    const myTime = new Date(date.getTime() + (8 * 60 * 60 * 1000));

    const day = myTime.getUTCDate();
    const month = myTime.getUTCMonth() + 1;
    const year = myTime.getUTCFullYear();

    let hours = myTime.getUTCHours();
    const minutes = myTime.getUTCMinutes();
    const seconds = myTime.getUTCSeconds();

    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;

    const minStr = minutes < 10 ? '0' + minutes : minutes;
    const secStr = seconds < 10 ? '0' + seconds : seconds;

    return `${month}/${day}/${year}, ${hours}:${minStr}:${secStr} ${ampm}`;
  };

  const isAdditional = receiptData.payment_type === 'additional';
  const paymentTypeLabel = isAdditional ? 'Additional Payment' : 'Original Payment';
  const accentColor = isAdditional ? '#dc3545' : '#007BFF';

  return (
    <View className="flex-1 bg-white" style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 py-3 border-b border-gray-100">
        <Text className="font-interBold text-lg text-gray-800">Parking Session</Text>
        <TouchableOpacity className="p-2 bg-gray-100 rounded-full">
          <User size={20} color="#333" />
        </TouchableOpacity>
      </View>

      <ScrollView className="flex-1 px-6 pt-6">
        <Text className="font-manrope text-2xl font-bold text-center text-gray-900 mb-6">
          Payment Receipt
        </Text>

        {/* Receipt Card */}
        <View className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden mb-6"
          style={{
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.1,
            shadowRadius: 8,
            elevation: 3,
          }}>
          <View className="h-2 w-full" style={{ backgroundColor: accentColor }} />
          <View className="p-5">
            {/* Payment Type Badge */}
            <View className="items-center mb-4">
              <View
                className="px-4 py-1.5 rounded-full"
                style={{ backgroundColor: isAdditional ? '#FFF3CD' : '#E8F5E9' }}
              >
                <Text
                  className="font-interBold text-[13px]"
                  style={{ color: isAdditional ? '#856404' : '#2E7D32' }}
                >
                  {paymentTypeLabel}
                </Text>
              </View>
            </View>

            {receiptData.receipt_number && (
              <View className="flex-row justify-between mb-4 pb-4 border-b border-dashed border-gray-200">
                <Text className="font-inter text-gray-500">Receipt No.</Text>
                <Text className="font-interBold text-gray-900">{receiptData.receipt_number}</Text>
              </View>
            )}
            <View className="flex-row justify-between mb-4 pb-4 border-b border-dashed border-gray-200">
              <Text className="font-inter text-gray-500">License Plate</Text>
              <Text className="font-interBold text-gray-900">{sessionData.license_plate}</Text>
            </View>
            <View className="flex-row justify-between mb-4 pb-4 border-b border-dashed border-gray-200">
              <Text className="font-inter text-gray-500">Entry Time</Text>
              <Text className="font-interBold text-gray-900">{formatDate(sessionData.entry_time)}</Text>
            </View>
            <View className="flex-row justify-between mb-4 pb-4 border-b border-dashed border-gray-200">
              <Text className="font-inter text-gray-500">Payment Date</Text>
              <Text className="font-interBold text-gray-900">{formatDate(receiptData.payment_date)}</Text>
            </View>
            <View className="flex-row justify-between mb-4 pb-4 border-b border-solid border-gray-200">
              <Text className="font-inter text-gray-500">Method</Text>
              <Text className="font-interBold text-gray-900">{receiptData.payment_method}</Text>
            </View>

            <View className="flex-row justify-between items-center mt-2">
              <Text className="font-interBold text-lg text-gray-900">TOTAL PAID</Text>
              <Text className="font-manrope text-2xl font-bold" style={{ color: accentColor }}>
                RM {Number(receiptData.total_amount).toFixed(2)}
              </Text>
            </View>
          </View>
        </View>

        {/* Grace Period Info */}
        {sessionData.grace_end_time && (
          <View className="bg-blue-50 p-4 rounded-lg mb-4">
            <Text className="font-interBold text-[#0056b3] text-center text-sm mb-1">
              Grace Period Deadline
            </Text>
            <Text className="font-inter text-[#0056b3] text-center text-sm">
              Please exit before {formatDate(sessionData.grace_end_time)}
            </Text>
          </View>
        )}

        <View className="bg-blue-50 p-4 rounded-lg mb-8">
          <Text className="font-inter text-[#0056b3] text-center text-sm">
            Please note: You must exit the parking area within 15 minutes of payment.
          </Text>
        </View>
      </ScrollView>

      {/* Footer Actions */}
      <View className="px-6 py-4 bg-white">
        <TouchableOpacity
          className="w-full h-[56px] bg-[#007BFF] rounded-lg items-center justify-center mb-4"
          onPress={handleDownloadPDF}
        >
          <Text className="font-interBold text-white text-[16px]">Download PDF</Text>
        </TouchableOpacity>

        <TouchableOpacity
          className="w-full h-[40px] items-center justify-center"
          onPress={handleReturnHome}
        >
          <Text className="font-interBold text-[#007BFF] text-[16px]">Return to Dashboard</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
